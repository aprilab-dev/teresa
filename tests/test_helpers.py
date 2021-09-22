import pytest
from teresa import helpers


@pytest.mark.parametrize("lat, lon", [(39., 116.)])
def test_latlon_to_city(lat, lon):
    city_nearest = helpers.latlon_to_city(lat, lon)
    assert city_nearest == "cn_beijing"
