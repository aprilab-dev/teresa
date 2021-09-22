import pytest
from teresa import helpers


@pytest.mark.parametrize("lat, lon", [(39, 116)])
def test_lat_lon_to_city(lat: float, lon: float):
    city_nearest = helpers.lat_lon_to_city(lat, lon)
    assert city_nearest == "baodingshi"
