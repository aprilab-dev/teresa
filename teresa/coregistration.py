from __future__ import annotations

import os
import abc
from . import graphs
from . import processor
from .log import log_config

# https://stackoverflow.com/questions/46641078/how-to-avoid-circular-dependency-caused-by-type-hinting-of-pointer-attributes-in
import typing

if typing.TYPE_CHECKING:
    from . import stack

logger = log_config()


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
        # administritive stuff
        ...

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
            "coregistration",
            self.slc_pair.slave.date,  # sort in dates
            f"iw{nsubswath}",
        )

        logger.info(
            "/COREGISTERING/ master %s and slave %s for swath IW%s:",
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

        logger.debug(f"COMPLETED /COREGISTERING/ slave {self.slc_pair.slave.date}.")
        self.slc_pair.slave.append(destination=output_path)

        if self.dry_run:
            pass  # do something?
        return self

    def _merge(self):

        graph = graphs.GptGraphS1Merge.generate()

        output_path = os.path.join(
            self.output_dir,
            "coregistration",
            self.slc_pair.slave.date,
            "merged",  # save in merged directory
        )

        logger.info(f"/MERGING/ subswaths of image {self.slc_pair.slave.date}")

        input_subswaths = {
            f"input_subswath{i+1}": path + ".dim"  # merge takes in .dim file
            for i, path in enumerate(self.slc_pair.slave.destination)
        }  # formating input swath paths

        self._processor.process(  # concrete implementation of the logic
            graph, output_path=output_path, **input_subswaths, dry_run=self.dry_run
        )

        logger.debug(
            f"COMPLETED /MERGING/ subswaths of image {self.slc_pair.slave.date}."
        )

        if self.dry_run:
            pass  # not sure what to do here, leave it blank for now.
        return self

    def _finalize(self):
        pass  # the logic for cleaning up

    def _prune(self):
        pass  # prune unneccessary files


class TSXCoregistration(Coregistration):
    def __init__(self):
        pass

    def coregistration(self):
        pass
