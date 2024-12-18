import os
import shutil
from teresa.stack import Sentinel1SlcImage


def create_multiple_masters_multiple_slaves(tmpdir):
    test_slc_dir = tmpdir.mkdir("multiple_masters_multiple_slaves")
    slcs = [
        "S1A_IW_SLC__1SDV_20210507T104527_20210507T104553_037781_047584_C9C5",
        "S1A_IW_SLC__1SDV_20210507T104502_20210507T104529_037781_047584_0263",
        "S1A_IW_SLC__1SDV_20210519T104527_20210519T104554_037956_047AD0_1750",
        "S1A_IW_SLC__1SDV_20210519T104502_20210519T104529_037956_047AD0_D69B",
    ]
    for slc in slcs:
        test_slc_dir.join(slc).write("multiple masters, multiple slaves")
    return test_slc_dir, {"20210507": 2, "20210519": 2}


def create_multiple_masters_single_slave(tmpdir):
    test_slc_dir = tmpdir.mkdir("multiple_masters_single_slave")
    slcs = [
        "S1A_IW_SLC__1SDV_20210507T104527_20210507T104553_037781_047584_C9C5",
        "S1A_IW_SLC__1SDV_20210507T104502_20210507T104529_037781_047584_0263",
        "S1A_IW_SLC__1SDV_20210519T104527_20210519T104554_037956_047AD0_1750",
    ]
    for slc in slcs:
        test_slc_dir.join(slc).write("multiple masters, single slaves")
    return test_slc_dir, {"20210507": 2, "20210519": 1}


def create_single_master_multiple_slaves(tmpdir):
    test_slc_dir = tmpdir.mkdir("single_master_multiple_slaves")
    slcs = [
        "S1A_IW_SLC__1SDV_20210507T104527_20210507T104553_037781_047584_C9C5",
        "S1A_IW_SLC__1SDV_20210519T104527_20210519T104554_037956_047AD0_1750",
        "S1A_IW_SLC__1SDV_20210519T104502_20210519T104529_037956_047AD0_D69B",
    ]
    for slc in slcs:
        test_slc_dir.join(slc).write("single master, multiple slaves")
    return test_slc_dir, {"20210507": 1, "20210519": 2}


def create_single_master_single_slave(tmpdir):
    test_slc_dir = tmpdir.mkdir("single_master_single_slave")
    slcs = [
        "S1A_IW_SLC__1SDV_20210507T104527_20210507T104553_037781_047584_C9C5",
        "S1A_IW_SLC__1SDV_20210519T104527_20210519T104554_037956_047AD0_1750",
    ]
    for slc in slcs:
        test_slc_dir.join(slc).write("single master, single slave")
    return test_slc_dir, {"20210507": 1, "20210519": 1}


def create_stacks(tmpdir):
    # creat a stack with more than 1 slaves.
    test_slc_dir = tmpdir.mkdir("stacks")
    slcs = [
        "S1A_IW_SLC__1SDV_20210507T104527_20210507T104553_037781_047584_C9C5",
        "S1A_IW_SLC__1SDV_20210507T104502_20210507T104529_037781_047584_0263",
        "S1A_IW_SLC__1SDV_20210519T104527_20210519T104554_037956_047AD0_1750",
        "S1A_IW_SLC__1SDV_20210519T104502_20210519T104529_037956_047AD0_D69B",
        "S1A_IW_SLC__1SDV_20210401T104500_20210401T104527_037256_046373_4E43",
        "S1A_IW_SLC__1SDV_20210401T104525_20210401T104552_037256_046373_5EE2",
    ]
    for slc in slcs:
        test_slc_dir.join(slc).write("stacks")
    return test_slc_dir, {"20210507": 2, "20210519": 2, "20210401": 2}


def create_slcimage(date, sourcedir):
    # 根据日期和 source 创建一个 Sentinel1SlcImage 对象，以供 FindBusrts 单元测试使用。
    slc_img = Sentinel1SlcImage(date=date)
    slc_img.sourcedir = sourcedir
    if os.path.exists(os.path.join(sourcedir, date)):  # 确保目录下不存在已有的 date 文件夹
        shutil.rmtree(os.path.join(sourcedir, date))
    source = tuple(os.path.join(sourcedir, fzip) for fzip in os.listdir(sourcedir))
    for subswath in ("IW1", "IW2", "IW3"):
        subswath_source = getattr(slc_img, subswath)
        subswath_source["source"] = source
    return slc_img
