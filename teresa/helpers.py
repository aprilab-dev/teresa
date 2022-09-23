import os
import re
import glob

import geojson
import requests
import logging
import zipfile
import numpy as np

from lxml import etree
from shapely.geometry import shape, Polygon
from pypinyin import lazy_pinyin as pinyin

logger = logging.getLogger("sLogger")

API_KEY = "B5EBZ-W2GCI-Q23GO-5RJTM-YRZL7-WJBHO"


# define a customized API error
class QQMapApiError(Exception):
    def __init__(self, message):
        self.message = message


def latlon_to_city(lat: float, lon: float) -> str:
    """return city name from lat and lon coordinates. Current function only
    supports China. If the city is not in China, return "ABOARD". If the city
    is in China, return "cn_xxxxxx" where "xxxxxx" is the city name.
    """

    url = "https://apis.map.qq.com/ws/geocoder/v1/?location={},{}&key={}".format(
        lat, lon, API_KEY
    )

    try:
        content = requests.get(url, timeout=60).json()
    except requests.exceptions.Timeout:
        return "TIMEOUT"

    if content["status"] != 0:
        logger.error(
            "ERROR %s: https://lbs.qq.com/service/webService/webServiceGuide/status",
            content["message"],
        )
        raise QQMapApiError(content["message"])
    if content["result"]["ad_info"]["nation_code"] != "156":
        return "ABOARD"

    nearest_city = pinyin(content["result"]["address_component"]["city"])
    nearest_city = nearest_city[:-1] if nearest_city[-1] == "shi" else nearest_city
    return "cn_" + "".join(nearest_city)

class FindBursts:
    """根据输入的 AOI 寻找影像中对应的 subswath 和 burst

    Parameters
    ----------
    sourcedir : str
        S1 原始 zip 文件的存放路径，目录下可以存放其他文件
    geojson: str
            目标区域 geojson 文件的绝对存储路径
    """
    def __init__(self, slc_image, geo_json: str):
        self.slc_image = slc_image
        self.aoi = self._geojson2polygon(geo_json)
        self.meta_sourcedir = os.path.join(os.path.dirname(slc_image.source[0]), slc_image.date)
        self._extract_meta()

    def _extract_meta(self):
        """#DEPRECATED: 这个 function 应该后面没有啥用了。
        extract 是读取:obj:`Sentinel1SlcImage` 类中的元数据所需要的方法。
        """
        def _unzip(fzip):
            # 将某一个 SentinelSlcImage 中的所有条带 xml 文件解压到一个
            try:
                zip_file = zipfile.ZipFile(fzip)
            except:
                logger.error(f"{fzip} wrong")
            for fxml in zip_file.namelist():
                re_matched = re.match(r"(.*)/annotation/(s1.*vv.*)", fxml)
                if not re_matched:
                    continue
                zip_file.extract(fxml, self.meta_sourcedir)
        # 解压
        for fzip in self.slc_image.source: # 此处是 source 而不是 sourcedir，因为是只提取一个对象的元数据，这个对象有可能包含多个数据。
            _unzip(fzip)
        return self

    def _read_xml(self, xml_file: str) -> dict:
        """Extract useful information in xml file into a dictionary

        Examples
        -------
        xml_info :
            {"lines": [0, 1, 2, ...], "pixels": [2, 3, 4, ...], ...}
        """
        xml = etree.parse(xml_file, etree.XMLParser())
        line_per_burst, numbers_per_subswath = int(xml.xpath("//linesPerBurst/text()")[0]), int(xml.xpath("//numberOfLines/text()")[0])
        lines, pixels = list(map(int, xml.xpath("//line/text()"))), list(map(int, xml.xpath("//pixel/text()")))
        longitudes, latitudes = list(map(float, xml.xpath("//longitude/text()"))), list(map(float, xml.xpath("//latitude/text()")))
        points_info = np.array([lines, pixels, longitudes, latitudes])
        burst_number = numbers_per_subswath // line_per_burst
        self.xml_info = {
            "points_info": points_info,
            "lines_per_burst": line_per_burst,
            "burst_number": burst_number
        }

    def _geojson2polygon(self, geojson_file: str) -> Polygon:
        """
        Convert geojson file to polygon
        """
        with open(geojson_file) as f:
            geojson_context = geojson.load(f)
        try:
            boundary = shape(geojson_context["features"][0]["geometry"])
        except:
            boundary = shape(geojson_context)
        return boundary

    def find_burst_in_overlap(self, overlap) -> int:
        """计算 overlap 在每个 subswath 上对应的起止 burst

        Parameters
        ---------
        overlap : polygon
            AOI 与该 subswath 相交的区域

        Returns
        -------
        burst_start : int
            burst 起始编号
        burst_end : int
            burst 截止编号
        """
        points_info, lines_per_burst, burst_number = (
            self.xml_info["points_info"],
            int(self.xml_info["lines_per_burst"]),
            int(self.xml_info["burst_number"]),
        )
        lonlat = points_info[2:4].T
        coefficient = np.concatenate(
            (np.ones((lonlat.shape[0], 1)), lonlat),
            axis=1,
        )
        w0, w1, w2 = np.linalg.lstsq(coefficient, points_info[0], rcond=None)[0]
        coordinates = list(overlap.exterior.coords)
        bursts = []
        for lon, lat in coordinates:
            line = w0 + w1 * lon + w2 * lat
            burst = int(line) // lines_per_burst + 1
            if burst < 1:
                burst = 1
            elif burst > burst_number:
                burst = burst_number
            bursts.append(burst)
            burst_start, burst_end = min(bursts), max(bursts)
        return burst_start, burst_end

    def xml2polygon(self, fxml):
        self._read_xml(fxml)
        points_info = self.xml_info["points_info"]
        up_index = np.where(points_info[0] == 0)
        low_index = np.where(points_info[0] == np.max(points_info[0]))
        left_index = np.where(points_info[1] == 0)
        right_index = np.where(points_info[1] == np.max(points_info[1]))
        left_up_corner = points_info[2:4, np.intersect1d(up_index, left_index)].tolist()
        right_up_corner = points_info[
            2:4, np.intersect1d(up_index, right_index)
        ].tolist()
        right_low_corner = points_info[
            2:4, np.intersect1d(low_index, right_index)
        ].tolist()
        left_low_corner = points_info[
            2:4, np.intersect1d(low_index, left_index)
        ].tolist()
        coordinates = []
        for corner in (left_up_corner, right_up_corner, right_low_corner, left_low_corner, left_up_corner):
            coordinates.append([corner[0][0], corner[1][0]])
        xml_boundary = Polygon(coordinates)
        return xml_boundary

    def get_burst_source(self, iw):
        """Returns一个字典，字典的 key 是 AOI 对应的 subswath 编号，key 的值是 AOI 在该 subswath 上所对应 burst 的起止编号

        Parameters
        ----------
        file_name : str
            sourcedir 下 S1 原始文件名称

        Returns
        -------
        swath_burst : dict
            返回的字典中包含覆盖 AOI 的最小条带信息，比如返回值是 {'IW1':[2,3], 'IW2':[3,3]}，对应的第一个条带的 第2，3 burst 和第二个条带
            的 第3 burst
        """
        # minimum_overlappings = {}
        source, bursts_start, bursts_end = (), (), ()
        meta_dir = self.meta_sourcedir
        for safe_file in os.listdir(meta_dir):
            fname = os.path.basename(self.slc_image.source[0]).split(".")[0]
            xml_dir = os.path.join(meta_dir, safe_file, "annotation")
            xml_path = glob.glob(os.path.join(xml_dir, f"s1*{iw}*"))[0]
            subswath_boundary = self.xml2polygon(xml_path) # Polygon
            overlapping_boundary = None if subswath_boundary.intersection(self.aoi).is_empty else subswath_boundary.intersection(self.aoi)
            if not overlapping_boundary:
                continue
            zip_path = os.path.join(os.path.dirname(meta_dir), fname + ".zip")
            source += (zip_path,)
            burst_start, burst_end = self.find_burst_in_overlap(overlapping_boundary)
            bursts_start += (max(burst_start - 1, 1),)
            bursts_end += (min(burst_end + 1, 9),)
        return bursts_start, bursts_end, source

    def get_minimum_overlapping(self) -> dict:
        index_and_source = {}
        for iw in ("IW1", "IW2", "IW3"):
            start_bursts, end_bursts, source = self.get_burst_source(iw.lower()) # 获取此 subswath 的起止编号和此 subswath 需要的影像数据。
            if not (start_bursts and end_bursts):
                index_and_source[iw] = {"first_burst_index": 0, "last_burst_index": 0, "source": ()}
                continue
            start_burst, end_burst = max(start_bursts), min(end_bursts)
            index_and_source[iw] = {"first_burst_index": start_burst, "last_burst_index": end_burst, "source": source}
        return index_and_source