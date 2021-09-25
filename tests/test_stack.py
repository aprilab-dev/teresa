import os
import pytest
from teresa import stack, log


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


mocked_s1_slcstack = [
    create_multiple_masters_multiple_slaves,
    create_multiple_masters_single_slave,
    create_single_master_multiple_slaves,
    create_single_master_single_slave,
]


@pytest.mark.parametrize("mocked", mocked_s1_slcstack)
def test_sentinel1_slcstack_load(tmpdir, mocked):
    source_dir, slc_len = mocked(tmpdir)
    tmp_stack = stack.Sentinel1SlcStack(sourcedir=source_dir).load()
    for key, value in tmp_stack.slc.items():
        # check if the length of loaded images are correct (check the predefined dictionary)
        assert len(value.source) == slc_len[key]


@pytest.mark.parametrize("mocked", mocked_s1_slcstack)
def test_sentinel1_slcstack_coregister(tmpdir, mocked):
    source_dir, slc_len = mocked(tmpdir)
    tmp_stack = stack.Sentinel1SlcStack(sourcedir=source_dir).load()
    tmp_stack.coregister(master="20210507", output=source_dir)
    # check if output is in the log
    assert os.path.join(source_dir, "coregistration") in open(log.LOG_FNAME).read()


def test_slcimage_append():
    # create a dummy SLCImage object
    dummy_slcimage = stack.SlcImage(date="20210926")
    dummy_slcimage.source = ("dummy_location1", "dummy_location2")  # type: ignore
    dummy_slcimage.destination = ("dummy_output1", "dummy_output2")  # type: ignore
    # update the object
    dummy_slcimage.append(source="dummy_location3", destination="dummy_output3")
    # check if the object is updated
    assert dummy_slcimage.source == ("dummy_location1", "dummy_location2", "dummy_location3")
    assert dummy_slcimage.destination == ("dummy_output1", "dummy_output2", "dummy_output3")
