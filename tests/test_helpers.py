import pytest

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
