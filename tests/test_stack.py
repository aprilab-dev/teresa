import os
import pytest
from teresa import stack, log
from teresa.coregistration import COREG_DIR, format_date
from . import conftest


mocked_s1_slcstack = [
    conftest.create_multiple_masters_multiple_slaves,
    conftest.create_multiple_masters_single_slave,
    conftest.create_single_master_multiple_slaves,
    conftest.create_single_master_single_slave,
    conftest.create_stacks,
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
    assert os.path.join(source_dir, COREG_DIR) in open(log.LOG_FNAME).read()
    # assert file existence
    pol = "VV"  # TODO: hardcoded for now
    master_datestr = format_date("20210507")
    for channel in ("i", "q"):  # in-phase & quadrature channels
        for suffix in ("img", "hdr"):
            master_filename = f"{channel}_{pol}_mst_{master_datestr}.{suffix}"
            assert os.path.isfile(
                os.path.join(source_dir, COREG_DIR,"master","merged.data",master_filename)
            )


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
