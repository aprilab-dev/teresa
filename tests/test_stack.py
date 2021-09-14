import pytest
from teresa import stack


@pytest.fixture(autouse=True)
def test_create_file(tmpdir):
    """Create a temporary folder containing simulated S1 files.
    """
    test_slc_dir = tmpdir.mkdir("slc").mkdir("cn_xian_s1_asc_iw")
    slcs = [
        "S1A_IW_SLC__1SDV_20210401T104500_20210401T104527_037256_046373_4E43",
        "S1A_IW_SLC__1SDV_20210507T104527_20210507T104553_037781_047584_C9C5",
        "S1A_IW_SLC__1SDV_20210401T104525_20210401T104552_037256_046373_5EE2",
        "S1A_IW_SLC__1SDV_20210519T104502_20210519T104529_037956_047AD0_D69B",
        "S1A_IW_SLC__1SDV_20210507T104502_20210507T104529_037781_047584_0263",
        "S1A_IW_SLC__1SDV_20210519T104527_20210519T104554_037956_047AD0_1750"
    ]
    for slc in slcs:
        test_slc_dir.join(slc).write("# sample SLC data")

    return test_slc_dir


def test_sentinel1slcstack_load(test_create_file):
    tmp_stack = stack.Sentinel1SlcStack(sourcedir=test_create_file).load()
    # iterate over a dict
    for _, value in tmp_stack.slc.items():
        assert len(value.source) == 2  # check if size of each slc is 2


def test_sentinel1slcstack_coregister(test_create_file):
    tmp_stack = stack.Sentinel1SlcStack(sourcedir=test_create_file).load()
    tmp_stack.coregister(master="20210401", output=test_create_file)
    # TODO: fill in the blank