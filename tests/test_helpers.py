import os
import pytest

from tests import conftest
from teresa import helpers


test_data_latlon_to_city = [
    ((39.994910, 116.474848), "cn_beijing"),
    ((34.243124, 108.912203), "cn_xian"),
    ((52.007490, 4.356293), "ABOARD"),
]


@pytest.mark.parametrize("input, desired", test_data_latlon_to_city)
def test_latlon_to_city(input, desired):
    assert desired == helpers.latlon_to_city(*input)


test_error_latlon_to_city = [((91.0, 118.0)), ((24.2, 181.0))]


@pytest.mark.parametrize("input", test_error_latlon_to_city)
def test_latlon_to_city_valueerror(input):
    with pytest.raises(helpers.QQMapApiError):
        helpers.latlon_to_city(*input)


test_data_find_bursts = [
    (
        "POLYGON((118.4939 36.8231,117.446 35.7963,118.7813 34.2381,120.5686 35.9625,119.8731 36.4895,118.4939 36.8231))",
        3,
        18,
        2,
    ),
    (None, 1, 999, 2),
    (
        "POLYGON((119.1082 34.7146,118.4832 34.071,119.4352 33.5379,119.641 34.21,119.1082 34.7146))",
        1,
        4,
        1,
    ),
]


@pytest.mark.parametrize(
    "polygon, first_burst_index, last_burst_index, source_number", test_data_find_bursts
)
def test_find_bursts(polygon, first_burst_index, last_burst_index, source_number):
    slc_img = conftest.create_slcimage(
        date="20210822",
        sourcedir=os.path.join(os.path.dirname(__file__), "aux/s1/sourcedir"),
    )
    if polygon:
        slc_img.crop(aoi=polygon)
        assert slc_img.IW1["first_burst_index"] == first_burst_index
        assert slc_img.IW3["last_burst_index"] == last_burst_index
        assert len(slc_img.IW1["source"]) == source_number
    else:  # 当不进行 crop 时，起止 burst 为 1 和 999
        assert slc_img.IW1["first_burst_index"] == first_burst_index
        assert slc_img.IW3["last_burst_index"] == last_burst_index
        assert len(slc_img.IW1["source"]) == source_number


# test_find_bursts(
#     "POLYGON((119.1082 34.7146,118.4832 34.071,119.4352 33.5379,119.641 34.21,119.1082 34.7146))",
#     1,
#     4,
#     1,
# )
