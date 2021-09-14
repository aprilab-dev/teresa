import pypinyin
import requests

API_KEY = "B5EBZ-W2GCI-Q23GO-5RJTM-YRZL7-WJBHO"


def lat_lon_to_city(lat: float, lon: float) -> str:
    """Convert a point with latitude and longitude to its nearest city"""
    try:
        url_request = "https://apis.map.qq.com/ws/geocoder/v1/?location={},{}&key={}&get_poi=1".format(
            lat, lon, API_KEY
        )
        data_flow = requests.get(url_request, timeout=120)
        text_json = data_flow.json()
        address_component = text_json["result"]["address_component"]
        city_nearest = address_component["city"]
        city_nearest_pinyin_list = pypinyin.lazy_pinyin(city_nearest)
        city_nearest_pinyin = "".join(city_nearest_pinyin_list)
        return city_nearest_pinyin
    except:
        print("time out!")
