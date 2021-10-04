from __future__ import annotations

import os
import re
import abc
import json
import shutil
import logging
from . import graphs
from . import processor
from .log import LOG_FNAME
from datetime import datetime

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
    @abc.abstractmethod
    def coregister(self):
        ...


class Sentinel1Coregistration(Coregistration):
    # concrete creater
    def __init__(
        self,
        slc_pair: stack.SlcPair,
        output_dir: str,
        polarization: str = "vv",
        dry_run: bool = True,
        coreg_processor: processor.GptProcessor = processor.GptProcessor(),
    ):
        self.graph = "None"
        self.slc_pair = slc_pair
        self.output_dir = output_dir
        self.polarization = polarization
        self.dry_run = dry_run
        self._processor = coreg_processor  # interface

    def coregister(self):
        self._prepare()
        self._coregister()
        self._merge()
        self._finalize()

    def _prepare(self):
        self._serialize()  # serialize the output into a json file

    def _coregister(self):
        # the lofic for swath coregistration.
        # The concrete implementation is actually in _subswath_coregister.
        for nsubswath in range(1, 4):  # starts from 1
            self._coregister_subswath(nsubswath)

    def _coregister_subswath(self, nsubswath: int):
        """TODO: add description."""

        graph = graphs.GptGraphS1Coreg.generate(self.slc_pair)

        # format gpt input
        master_files = ",".join([source for source in self.slc_pair.master.source])
        slave_files = ",".join([source for source in self.slc_pair.slave.source])
        output_path = os.path.join(
            self.output_dir,
            COREG_DIR,
            self.slc_pair.slave.date,  # sort in dates
            f"iw{nsubswath}",
        )

        logger.info(
            "COREGISTERING master %s and slave %s for swath IW%s:",
            self.slc_pair.master.date,
            self.slc_pair.slave.date,
            nsubswath,
        )

        # Execute the actual coregistration
        self._processor.process(
            graph,
            subswath=f"IW{nsubswath}",
            polorization=self.polarization.upper(),
            master_files=master_files,
            slave_files=slave_files,
            output_path=output_path,
            dry_run=self.dry_run,
        )

        logger.info(f"COREGISTERING slave {self.slc_pair.slave.date} completed.")
        self.slc_pair.slave.append(destination=output_path)

        if self.dry_run:
            logger.debug("DRY-RUN: Creating dummy folders/files for testing purpose.")
            for i in range(1, 4):
                os.makedirs(output_path + ".data", exist_ok=True)
                open(output_path + ".dim", "w").close()

        return self

    def _merge(self):

        graph = graphs.GptGraphS1Merge.generate()

        output_path = os.path.join(
            self.output_dir,
            COREG_DIR,
            self.slc_pair.slave.date,
            "merged",  # save in merged directory
        )

        logger.info(f"MERGING subswaths of image {self.slc_pair.slave.date}:")

        input_subswaths = {
            f"input_subswath{i+1}": path + ".dim"  # merge takes in .dim file
            for i, path in enumerate(self.slc_pair.slave.destination)
        }  # formating input swath paths

        self._processor.process(  # concrete implementation of the logic
            graph, output_path=output_path, **input_subswaths, dry_run=self.dry_run
        )

        logger.info(f"MERGING image {self.slc_pair.slave.date} completed.")

        if self.dry_run:
            logger.debug("DRY-RUN: Creating dummy folders/files for testing purpose.")
            os.makedirs(output_path + ".data", exist_ok=True)
            open(output_path + ".dim", "w").close()
            pol = self.polarization.upper()
            master_datestr = format_date(self.slc_pair.master.date)
            for channel in ("i", "q"):  # in-phase & quadrature channels
                for suffix in ("img", "hdr"):
                    master_filename = f"{channel}_{pol}_mst_{master_datestr}.{suffix}"
                    open(
                        os.path.join(output_path + ".data", master_filename), "w"
                    ).close()

        return self

    def _finalize(self):
        self._link_master()  # make a simlink to master date
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
        for channel in ("i", "q"):  # in-phase & quadrature channels
            for suffix in ("img", "hdr"):
                master_filename = f"{channel}_{pol}_mst_{master_datestr}.{suffix}"
                dst_file = os.path.join(dst_dir, "merged.data", master_filename)
                src_file = os.path.join(src_dir, "merged.data", master_filename)
                # copy if not exists
                if os.path.exists(dst_file):
                    logger.debug(f"{dst_file} already exists.")
                    if suffix == "img":  # remove img file if exists
                        os.remove(src_file)
                else:
                    logger.debug(f"Linking {src_file} to {dst_file}.")
                    shutil.move(src_file, dst_file)

        master_symlink = os.path.join(self.output_dir, COREG_DIR, "master")
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
