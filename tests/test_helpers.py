import os
import pytest
from tests.conftest import create_slcimage
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


polygons = [
    "POLYGON((118.4939 36.8231,117.446 35.7963,118.7813 \
            34.2381,120.5686 35.9625,119.8731 36.4895,118.4939 36.8231))",
    None,
]


@pytest.mark.parametrize("polygons", polygons)
def test_find_bursts(polygons):
    slc_img = create_slcimage(
        date="20210822", sourcedir=os.path.join(os.path.dirname(__file__), "aux/s1/sourcedir")
    )
    if polygons:
        slc_img.crop(aoi=polygons)
        assert slc_img.IW1["first_burst_index"] == 3
        assert slc_img.IW3["last_burst_index"] == 18
        assert len(slc_img.IW1["source"]) == 2
    else:  # 当不进行 crop 时，起止 burst 为 1 和 999
        assert slc_img.IW1["first_burst_index"] == 1
        assert slc_img.IW3["last_burst_index"] == 999
        assert len(slc_img.IW1["source"]) == 2
