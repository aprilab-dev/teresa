from pypinyin import lazy_pinyin as pinyin
import requests
from log import log_config

logger = log_config()

API_KEY = "B5EBZ-W2GCI-Q23GO-5RJTM-YRZL7-WJBHO"


def latlon_to_city(lat: float, lon: float) -> str:
    """Convert a point with latitude and longitude to its nearest city."""

    url = "https://apis.map.qq.com/ws/geocoder/v1/?location={},{}&key={}".format(
        lat, lon, API_KEY
    )
    
    try:
        content = requests.get(url, timeout=60).json()
    except requests.exceptions.Timeout:
        return  "TIMEOUT"

    if content["status"] != 0:
        logger.error(
            "ERROR %s: https://lbs.qq.com/service/webService/webServiceGuide/status",
            content["message"],
        )
    if content["result"]["ad_info"]["nation_code"] != "156":
        return "ABOARD"
    
    nearest_city = pinyin(content["result"]["address_component"]["city"])
    nearest_city = nearest_city[:-1] if nearest_city[-1] == "shi" else nearest_city
    return "cn_" + "".join(nearest_city)
