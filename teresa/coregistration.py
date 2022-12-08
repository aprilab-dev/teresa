import abc
import json
import logging
import os
import re
import shutil

from datetime import datetime
from itertools import product

from . import graphs
from . import processor
from .log import LOG_FNAME


# https://stackoverflow.com/questions/46641078/how-to-avoid-circular-dependency-caused-by-type-hinting-of-pointer-attributes-in
import typing

if typing.TYPE_CHECKING:
    from . import stack

logger = logging.getLogger("sLogger")

COREG_DIR = "coregistered"

format_date = lambda datestr: datetime.strptime(datestr, "%Y%m%d").strftime("%d%b%Y")


class CoregistrationError(RuntimeError):
    def __init__(self, message):
        self.message = message


class Coregistration(abc.ABC):
    def __init__(
        self,
        slc_pair,  # TODO stack 会调用 coregistration，如果此时增加 typehint，会导致循环调用
        output_dir: str,
        polarization: str = "vv",
        dry_run: bool = True,
        prune: bool = True,
        radarcode_dem: bool = False,  # by default don't radarcode dem
        coreg_processor: processor.GptProcessor = processor.GptProcessor(),
    ):
        # concrete implementation of init function
        self.processed_subswaths = ()
        self.slc_pair = slc_pair
        self.output_dir = output_dir
        self.polarization = polarization
        self.dry_run = dry_run
        self.prune = prune
        self.radarcode_dem = radarcode_dem
        self._processor = coreg_processor  # interface

    @abc.abstractmethod
    def coregister(self):
        ...

    def _radarcode_dem(self):
        """concrete implementation of geocoding DEM using the
        interferogram function in snap. The implementation of geocoding DEM
        should be the same regardless of the sensors. This is why we put this
        function into the parent class.
        """

        input_pair = os.path.join(
            self.output_dir, COREG_DIR, self.slc_pair.master.date, "merged.dim"
        )
        output_path = os.path.join(self.output_dir, COREG_DIR, "DEM")

        # Execute the actual coregistration
        self._processor.process(
            graph=graphs.GptGraph.radarcode_dem(),
            input_pair=input_pair,
            output_path=output_path,
            dry_run=self.dry_run,
        )

        if self.dry_run:
            master_datestr = format_date(self.slc_pair.master.date)
            logger.debug("DRY RUN: Creating dummy 'DEM' folder for testing purpose.")
            os.makedirs(os.path.join(output_path, "merged") + ".data", exist_ok=True)
            open(os.path.join(output_path, "merged") + ".dim", "w").close()
            open(os.path.join(output_path, "merged.data", "elevation.hdr"), "w").close()
            open(
                os.path.join(
                    output_path,
                    "merged.data",
                    f"coh_VV_{master_datestr}_{master_datestr}.hdr",
                ),
                "w",
            ).close()


class Sentinel1Coregistration(Coregistration):
    def coregister(self):
        self._prepare()
        self._coregister()
        self._merge()
        if self.radarcode_dem:  # if radarcode dem, do it before the prune
            self._radarcode_dem()
        self._finalize()

    def _prepare(self):
        self._serialize()  # serialize the output into a json file

    def _coregister(self):
        # the lofic for swath coregistration.
        # The concrete implementation is actually in _subswath_coregister.
        for nsubswath in ("IW1", "IW2", "IW3"):  # starts from 1
            self._coregister_subswath(nsubswath)

    def _coregister_subswath(self, nsubswath: str):
        """TODO: add description."""

        # format gpt input
        master_files = ",".join(
            [source for source in getattr(self.slc_pair.master, nsubswath)["source"]]
        )  # 获取该 subswath 中覆盖 aoi 的文件（或多个文件)
        slave_files = ",".join(
            [source for source in getattr(self.slc_pair.slave, nsubswath)["source"]]
        )

        if not master_files:  # 获取每个 subswath 对应的 source 文件，若为空，则无需处理此 subswath
            return self
        graph = graphs.GptGraphS1Coreg.generate(
            mfile=master_files.split(","), sfile=slave_files.split(",")
        )
        self.processed_subswaths += (
            nsubswath,
        )  # 将需要处理的 subswath 编号添加到一个元组中，此元组的作用有两个，一是判断需要 merge 的条带数选择对应的 xml 文件，另一个是 link_master 中伪造文件。
        output_path = os.path.join(
            self.output_dir,
            COREG_DIR,
            self.slc_pair.slave.date,  # sort in dates
            nsubswath,
        )

        if not self.dry_run:
            logger.info(  # logging before exeuution
                "COREGISTERING master %s and slave %s for swath %s:",
                self.slc_pair.master.date,
                self.slc_pair.slave.date,
                nsubswath,
            )

        master_bursts_indices = getattr(self.slc_pair.master, nsubswath)
        slave_bursts_indices = getattr(self.slc_pair.slave, nsubswath)

        # Execute the actual coregistration
        self._processor.process(
            graph,
            subswath=nsubswath,
            polorization=self.polarization.upper(),
            master_files=master_files,
            slave_files=slave_files,
            output_path=output_path,
            dry_run=self.dry_run,
            # add structure here
            master_first_burst=master_bursts_indices["first_burst_index"],
            master_last_burst=master_bursts_indices["last_burst_index"],
            slave_first_burst=slave_bursts_indices["first_burst_index"],
            slave_last_burst=slave_bursts_indices["last_burst_index"],
        )

        self.slc_pair.slave.append(destination=output_path)
        if not self.dry_run:
            logger.info(
                f"COREGISTERING slave {self.slc_pair.slave.date} swath IW{nsubswath} completed."
            )

        if self.dry_run:
            logger.debug("DRY RUN: Creating dummy folders/files for testing purpose.")
            for _ in range(1, 4):
                os.makedirs(output_path + ".data", exist_ok=True)
                open(output_path + ".dim", "w").close()

        return self

    def _merge(self):

        graph = graphs.GptGraphS1Merge.generate(self.processed_subswaths)

        output_path = os.path.join(
            self.output_dir,
            COREG_DIR,
            self.slc_pair.slave.date,
            "merged",  # save in merged directory
        )

        if not self.dry_run:
            logger.info(f"MERGING subswaths of image {self.slc_pair.slave.date}:")

        input_subswaths = {
            f"input_subswath{i+1}": path + ".dim"  # merge takes in .dim file
            for i, path in enumerate(self.slc_pair.slave.destination)
        }  # formating input swath paths

        self._processor.process(  # concrete implementation of the logic
            graph, output_path=output_path, **input_subswaths, dry_run=self.dry_run
        )

        if not self.dry_run:
            logger.info(f"MERGING image {self.slc_pair.slave.date} completed.")

        if self.dry_run:
            logger.debug("DRY RUN: Creating dummy folders/files for testing purpose.")
            os.makedirs(output_path + ".data", exist_ok=True)
            open(output_path + ".dim", "w").close()
            pol = self.polarization.upper()
            master_datestr = format_date(self.slc_pair.master.date)
            slave_datestr = format_date(self.slc_pair.slave.date)
            for channel, suffix in product(("i", "q"), ("img", "hdr")):
                master_filename = f"{channel}_{pol}_mst_{master_datestr}.{suffix}"
                slave_filename = f"{channel}_{pol}_slv_{slave_datestr}.{suffix}"
                for fn in (master_filename, slave_filename):
                    open(os.path.join(output_path + ".data", fn), "w").close()

        return self

    def _finalize(self):
        self._link_master()  # make a simlink to master date
        if self.prune:
            self._prune()  # prune unnecessary files
        return self

    def _link_master(self):
        # make a folder to include master files, and link to the "master" folder
        dst_dir = os.path.join(self.output_dir, COREG_DIR, self.slc_pair.master.date)
        src_dir = os.path.join(self.output_dir, COREG_DIR, self.slc_pair.slave.date)
        os.makedirs(dst_dir, exist_ok=True)
        os.makedirs(os.path.join(dst_dir, "merged.data"), exist_ok=True)

        pol = self.polarization.upper()
        master_datestr = format_date(self.slc_pair.master.date)
        for channel, suffix in product(
            ("i", "q"), ("img", "hdr")
        ):  # in-phase & quadrature channels
            # master_filename = f"{channel}_{pol}_mst_{master_datestr}.{suffix}"
            # 当只有 subwath 的数量等于 1 时，merged.data 里面的数据是 i_vv_mst_20210101.img，否则是 i_IW1_vv_mst_20210101.img 形式
            master_filename = (
                f"{channel}_{pol}_mst_{master_datestr}.{suffix}"
                if len(self.processed_subswaths) > 1
                else f"{channel}_{self.processed_subswaths[0]}_{pol}_mst_{master_datestr}.{suffix}"
            )

            dst_file = os.path.join(dst_dir, "merged.data", master_filename)
            src_file = os.path.join(src_dir, "merged.data", master_filename)
            # copy if not exists
            if os.path.exists(dst_file):
                logger.debug(f"{dst_file} already exists.")
                # if suffix == "img" and self.prune:  # remove img file if exists
                #     os.remove(src_file)
            else:
                logger.debug(f"Linking {src_file} to {dst_file}.")
                # if self.prune:  # 这一步 prune 个人理解去掉 shutil.move
                # shutil.move(src_file, dst_file)
                # else:
                shutil.copy2(src_file, dst_file)

        master_symlink = os.path.join(self.output_dir, COREG_DIR, "master")
        if not self.dry_run:
            logger.info(f"SOFT-LINKING {self.slc_pair.master.date} to 'master' folder.")
        if not os.path.exists(master_symlink):
            # make a symlinks to "master" folder
            os.symlink(dst_dir, master_symlink)
        return self

    def _prune(self):
        # remove the intermediate files
        for path in self.slc_pair.slave.destination:
            # remove subswaths files (only useful before merging)
            os.remove(path + ".dim")  # type: ignore
            shutil.rmtree(path + ".data")  # type: ignore

        # prune DEM folder if exists: remove all "coh" and "ifg" files
        dem_path = os.path.join(self.output_dir, COREG_DIR, "DEM")
        if not os.path.exists(dem_path):
            return self
        for root, dirs, files in os.walk(os.path.join(dem_path, "merged.data")):
            for file in files:
                if "ifg" in file or "coh" in file:
                    os.remove(os.path.join(root, file))  # type: ignore

        return self

    def _serialize(self):

        # last updated time
        last_updated = datetime.strptime(
            re.search(r"teresa_(.*).log", LOG_FNAME).group(1), "%Y-%m-%d_%H-%M-%S"  # type: ignore
        ).strftime("%Y/%m/%d %H:%M:%S")

        # metadata path
        metadata_path = os.path.join(self.output_dir, COREG_DIR, "meta.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {}
        # Update metadata
        if "master" in metadata and metadata["master"] != self.slc_pair.master.date:
            s = f"Master {self.slc_pair.master.date} does NOT match the master date {metadata['master']} in metafile!"
            logger.error(s)
            raise CoregistrationError(s)

        metadata["master"] = self.slc_pair.master.date
        metadata["log"] = os.path.join(os.getcwd(), LOG_FNAME)  # log file absolute path
        metadata["last_updated"] = last_updated
        if "slave" in metadata:
            metadata["slave"].append(self.slc_pair.slave.date)
        else:
            metadata["slave"] = [self.slc_pair.slave.date]  # list

        # create directory
        os.makedirs(os.path.join(self.output_dir, COREG_DIR), exist_ok=True)
        # update metadata
        with open(metadata_path, "w") as outfile:  # write
            json.dump(metadata, outfile)

        return self


class TSXCoregistration(Coregistration):
    def __init__(self):
        pass

    def coregistration(self):
        pass
