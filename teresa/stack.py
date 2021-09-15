import re
import os
import abc
from teresa import coregistration
from teresa.log import log_config

logger = log_config()


class SlcImage:
    def __init__(self, date: str):
        self.date = date
        self.source = ()  # use a tuple to store filenames


class SlcPair:
    def __init__(self, master: SlcImage, slave: SlcImage):
        self.master = master
        self.slave = slave

    def coregister(self, output_dir: str, dry_run: bool = True):
        # initialize a dictionary to store the coregistration results
        coregistration_settings = {"output_dir": output_dir, "dry_run": dry_run}
        coregistration.Sentinel1Coregistration(
            slc_pair=self, **coregistration_settings
        ).coregister()


class SlcStack(abc.ABC):
    @abc.abstractmethod
    def load(self):
        pass


class Sentinel1SlcStack(SlcStack):
    def __init__(self, sourcedir: str):
        self.slc = {}  # use a dict to store the SLCs
        self.sourcedir = sourcedir

    def load(self):
        """load all matched S1 SLCs from sourcedir."""
        for file in os.listdir(self.sourcedir):
            # https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-1-sar/naming-conventions
            if re.search(r"S1[A|B]_IW_SLC", file):
                # get the date from the filename
                acquisition = re.search(
                    r"S1[A|B]_IW_SLC_.+(20\d{6})T\d{6}_20\d{6}T\d{6}_.+", file
                ).group(1)
                # check if key exist
                if acquisition not in self.slc:
                    self.slc[acquisition] = SlcImage(date=acquisition)

                self.slc[acquisition].source += (
                    os.path.join(self.sourcedir, file),
                )  # update tuple

        return self

    def coregister(self, master: str, output: str, update: bool = False) -> None:
        # check if master is in the slc dict
        if master not in self.slc:
            logger.exception(f"The master date [{master}] is not in the stack.")
        for slave, _ in self.slc.items():
            SlcPair(
                master=self.slc[master], slave=self.slc[slave]
            ).coregister(output_dir=output, dry_run=False)
