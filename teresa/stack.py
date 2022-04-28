import re
import os
import abc
import logging
from teresa import coregistration as coreg
from .log import LOG_FNAME

logger = logging.getLogger("sLogger")


class SlcImage:

    """`SlcImage` 是对于单张 SLC 影像的一个抽象。里面包含了需要抽象一张 SLC 所需要的属性。
    `SlcImage` 中抽象的是所有 SLC 所共同所有的属性。

    Attributes
    ----------
    date : str
        单张 SLC 的影像获取时间。
    destination : tuple
        对应日期的所处理（配准）过后的 SLC 影像的存储路径（文件夹）。
    source : tuple
        对应日期的原始 1 级 SLC 影像路径（可以一个日期对应多个路径，用 tuple 存储。）
    """

    def __init__(self, date: str):
        """初始化`SlcImage`，初始化只需要给定对应的日期（`date`）即可。

        Parameters
        ----------
        date : str
        """
        self.date = date
        self.source = ()  # 仅在这里做初始化
        self.destination = ()  # 仅在这里做初始化

    def append(self, **kwargs):
        """`append()` 方法是用来为`SlcImage`类添加和更新属性的方法。`append()` 设置了该类
        可以添加和更新的属性。**目前** 可更新的属性只有 `source` 和 `destination` 两个。

        Parameters
        ----------
        **kwargs
            可以添加到 `SlcImage` 类中的 keyword argument。
        """

        # append a field of the object (we need to update because we use tuple
        # for source, destination, ...)
        for key, value in kwargs.items():
            assert (
                key in ("source", "destination")
            ), "Only 'source' and 'destination' are allowed to be updated!"
            self.__dict__[key] = self.__dict__[key] + (value,)


class Sentinel1SlcImage(SlcImage):

    """`Sentinel1SlcImage` 是 `SlcImage` 的子类，定义了一些只有 Sentinel-1 才有的属性和
    方法。
    """

    def __init__(self, date: str):
        """除了 `SlcImage` 的方法以外，S1 独有的属性是*所需要处理*的 subswaths 和 bursts 的
        个数（index），故对于每一个 subswaths 都定义了 `first_burst_index` 和 `last_burst_index`。
        因为 `teresa` 处理的 S1 目前仅限于 IW 模式，一定是三个 subswaths，故采用了一种“hardcoded”
        的方式来定义三个 subswaths 的属性如下：
            `self.IW1["first_burst_index"]=2`
            `self.IW1["last_burst_index"]=3`
            `self.IW3["first_burst_index"]=None`
            `self.IW3["last_burst_index"]=None`
        """
        super(Sentinel1SlcImage, self).__init__(date)
        for nsubswath in range(1, 4):  # initialize bursts indice for 3 subswath
            setattr(self, f"IW{nsubswath}", {"first_burst_index":1, "last_burst_index":999})

    def crop(self, aoi):
        """单个文件的 crop 业务逻辑发生在这里
        这个逻辑目前只有S1需要，所以不需要创建一个 abstract class
        """

        """
        业务逻辑如下：
        aoi = geojson2polyon(aoi)
        boundary = xml2polygon(self.source) <
        intersection = intersect(aoi, boundary)
        for nsubswath in range(1, 4):  # initialize bursts indice for 3 subswath
            first, last = _find_burst_in_intersection(intersection, meta)
            setattr(self, f"IW{nsubswath}", {"first_burst_index":first, "last_burst_index":last})
        """
        pass


class SlcPair:
    def __init__(self, master: SlcImage, slave: SlcImage):
        self.master = master
        self.slave = slave

    def coregister(self):
        pass


class Sentinel1SlcPair(SlcPair):
    def coregister(self, **coreg_settings):
        # coregistration_settings to coreg_settings to save a few spaces
        coreg.Sentinel1Coregistration(slc_pair=self, **coreg_settings).coregister()


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
                ).group(1)  # type: ignore
                # check if key exist
                if acquisition not in self.slc:
                    self.slc[acquisition] = Sentinel1SlcImage(date=acquisition)

                self.slc[acquisition].source += (
                    os.path.join(self.sourcedir, file),
                )  # update tuple

        return self

    def crop(self, aoi):
        """
        此函数根据 AoI “裁剪” S1 的数据集。注意，这个“裁剪”不是一个真实的“裁剪”，只是算出包含
        AoI 所需要的 bursts 是多少。在配准的过程中会选择相应的 bursts 进行裁剪后配准。
        """

        """
        crop() 中的逻辑应该是：
        想想看，为什么？？?

        for img, _ in self.slc.items():
            self.slc[img].crop(aoi=aoi)

        return self
        """
        pass

    def coregister(
        self,
        master: str,
        output: str,
        dry_run: bool = True,
        prune: bool= True,
        update: bool = False
    ) -> None:
        # check if master is in the slc dict
        if master not in self.slc:
            logger.critical(f"The master date [{master}] is not in the stack!")
            raise SystemExit(-1)  # return a -1 status

        """ coregistering the stack
        """
        completed_item=0
        for slave, _ in self.slc.items():
            if slave == master:
                continue  # does not make sense to coregister master to master
            Sentinel1SlcPair(
                master=self.slc[master],
                slave=self.slc[slave]
            ).coregister(
                output_dir=output,
                dry_run=dry_run,
                prune=prune
            )
            completed_item += 1
            logger.info(f"PROGRESS: {completed_item}/{len(self.slc.items())-1} completed.")

        """
        radarcode dem: for radarcoding we can coregister master with master.
        as a matter of fact, it doesn't matter which image we coregsiter to master
        when doing radarcoding of dem.
        """
        logger.info("RADARCODING DEM: Start.")

        Sentinel1SlcPair(
            master=self.slc[master],
            slave=self.slc[master]  # radarcode DEM
        ).coregister(
            output_dir=output,
            dry_run=dry_run,
            prune=prune,
            radarcode_dem=True,  # radarcode dem
        )

        logger.info("RADARCODING DEM: completed.")
        logger.info(f"Processing complete! Log is saved to {LOG_FNAME}")