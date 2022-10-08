import os
import re
import glob
import shapely.wkt

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

    url = "https://apis.map.qq.com/ws/geocoder/v1/?location={},{}&key={}".format(lat, lon, API_KEY)

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
    """输入 Sentinel1SlcImage 对象和 geojson 格式或 Polygon 字符串的 aoi 文件，计算每一个 subwath 所需的数据以及它们
    对应的起止 burst

    参数
    ---
    slc_image : Object
        S1 原始 zip 文件的存放路径，目录下可以存放其他文件
    aoi: str
        目标区域 geojson 文件的存储路径

    例子
    ---
    slc_image :
        输入的 slc_image 已经初始化 IW1, IW2, IW3 属性，以 IW1 属性为例，其初始化后的格式为
        {"first_burst_index": 1, "last_burst_index": 999,"fmeta": self.source}, 计算后属性变为
        {"first_burst_index": 2, "last_burst_index": 8,"fmeta": (source_iw)}，其中的 source_iw 为 IW1
        条带所需的所有数据。
    """

    def __init__(self, slc_image, aoi: str):
        """在对象初始化阶段，将 geojson 格式的 aoi 文件转为 Polygon，获取存放该 Sentinel1SlcImage 源文件的路径
        self.meta_sourcedir 并将这些源文件使用 self.extract_meta 提取出来。
        """
        self.slc_image = slc_image
        self.meta_sourcedir = os.path.join(slc_image.sourcedir, slc_image.date)
        self._extract_meta()
        if os.path.isfile(aoi):  # 发现实际使用时直接使用 ASF 的 Polygon 字符串更方便些，增加一个数据类型接口。
            self.aoi = self._geojson2polygon(aoi)
        else:
            self.aoi = shapely.wkt.loads(aoi)

    def _extract_meta(self):
        """提取输入对象中 source 属性下的所有 zip 文件的源文件，存放在工作目录下对应日期的目录下面。"""

        def _unzip(fzip):
            # 将一景 zip 格式的文件中的 xml 文件提取到目标目录。
            try:
                zip_file = zipfile.ZipFile(fzip)
            except:
                logger.error(f"{fzip} wrong")
            for fxml in zip_file.namelist():
                re_matched = re.match(r"(.*)/annotation/(s1.*vv.*)", fxml)
                if not re_matched:
                    continue
                zip_file.extract(fxml, self.meta_sourcedir)

        # 将该 Sentinel1SlcImage 对象 source 属性中的所有 zip 文件的 xml 文件提取。
        for fzip in self.slc_image.IW1["source"]:
            _unzip(fzip)

    def _read_xml(self, fxml: str) -> dict:
        """读取一个 xml 文件中所需的信息，存放到 self.xml_info 中，points_info 是一个 np.array 格式的数组，
        第一行至第四行以此是：行坐标，列坐标，经度，纬度，其每一列是一一对应的关系，这样可以使用矩阵固定它们之间的
        关系。
        """
        xml = etree.parse(fxml, etree.XMLParser())
        line_per_burst, numbers_per_subswath = int(xml.xpath("//linesPerBurst/text()")[0]), int(
            xml.xpath("//numberOfLines/text()")[0]
        )
        lines, pixels = list(map(int, xml.xpath("//line/text()"))), list(
            map(int, xml.xpath("//pixel/text()"))
        )
        longitudes, latitudes = list(map(float, xml.xpath("//longitude/text()"))), list(
            map(float, xml.xpath("//latitude/text()"))
        )
        points_info = np.array([lines, pixels, longitudes, latitudes])
        burst_number = numbers_per_subswath // line_per_burst
        self.xml_info = {
            "points_info": points_info,
            "lines_per_burst": line_per_burst,
            "burst_number": burst_number,
        }

    def _geojson2polygon(self, geojson_file: str) -> Polygon:
        """将 geojson 格式的文件转为 Polygon"""
        with open(geojson_file) as f:
            geojson_context = geojson.load(f)
        try:  # 不同方式建立的 geojson 文件格式可能会不同
            boundary = shape(geojson_context["features"][0]["geometry"])
        except:
            boundary = shape(geojson_context)
        return boundary

    def find_burst_in_overlap(self, overlap) -> int:
        """计算 aoi 与单个 subswath 相交区域在该 subswath 所对应的 burst 的起止编号。

        参数
        ---
        overlap : polygon
            AOI 与该 subswath 相交的区域

        返回
        ---
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
        coefficient = np.concatenate((np.ones((lonlat.shape[0], 1)), lonlat), axis=1)
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

    def xml2polygon(self, fxml: str) -> Polygon:
        """将单个 xml 文件转化为其对应的范围 Polygon"""
        self._read_xml(fxml)
        points_info = self.xml_info["points_info"]
        up_index = np.where(points_info[0] == 0)
        low_index = np.where(points_info[0] == np.max(points_info[0]))
        left_index = np.where(points_info[1] == 0)
        right_index = np.where(points_info[1] == np.max(points_info[1]))
        left_up = points_info[2:4, np.intersect1d(up_index, left_index)].tolist()
        right_up = points_info[2:4, np.intersect1d(up_index, right_index)].tolist()
        right_low = points_info[2:4, np.intersect1d(low_index, right_index)].tolist()
        left_low = points_info[2:4, np.intersect1d(low_index, left_index)].tolist()
        coordinates = []
        for corner in (left_up, right_up, right_low, left_low, left_up):
            coordinates.append([corner[0][0], corner[1][0]])
        xml_boundary = Polygon(coordinates)
        return xml_boundary

    def get_bursts_and_source(self, iw: str):
        """Sentinel1SlcImage 有IW1，IW2，IW3 三个属性，此函数计算该条带所需的影像数据，以及在每景影像上对应的 burst 起止编号。
        止编号。

        参数
        ---
        iw : str
            条带名称，有 IW1，IW2，IW3

        例子
        ---
        如果输入的参数为 IW1，假设该条带需要两景影像，1.zip 和 2.zip，在 1.zip 影像中对应的 burst 起止编号为 5-9，在 2.zip 中
        对应的 burst 的起止编号为 1-3，则返回的 bursts_start，bursts_end 和 source 的值分别为 (5,1)，(9,3)，(../1.zip, ../2.zip)
        """
        source, bursts_start, bursts_end = (), (), ()
        meta_dir = self.meta_sourcedir
        for safe_file in os.listdir(meta_dir):
            fname = safe_file.split(".")[0]
            xml_dir = os.path.join(meta_dir, safe_file, "annotation")
            xml_path = glob.glob(os.path.join(xml_dir, f"s1*{iw}*"))[0]
            subswath_boundary = self.xml2polygon(xml_path)  # Polygon
            overlapping_boundary = (
                None
                if subswath_boundary.intersection(self.aoi).is_empty
                else subswath_boundary.intersection(self.aoi)
            )
            if not overlapping_boundary:
                continue
            zip_path = os.path.join(os.path.dirname(meta_dir), fname + ".zip")
            source += (zip_path,)
            burst_start, burst_end = self.find_burst_in_overlap(overlapping_boundary)
            bursts_start += (max(burst_start - 1, 1),)
            bursts_end += (min(burst_end + 1, 9),)
        return bursts_start, bursts_end, source

    def get_minimum_overlapping(self) -> dict:
        """此函数为 crop 的接口函数

        例子
        ---
        index_and_source : dict
            字典的 key 值为 subwath 编号，为 IW1，IW2，IW3。value 值为每个条带对应的起始 burst 编号和终止 burst 编号，以及其所需的
            zip 文件，以 IW1 为例，假设该条带需要两景影像，1.zip 和 2.zip，在 1.zip 影像中对应的 burst 起止编号为 5-9，在 2.zip 中
            对应的 burst 的起止编号为 1-3。其在 index_and_source 中的形式为 {"IW1": {"first_burst_index": 5,
            "last_burst_index": 12, "source": (../1.zip, ../2.zip)}
        """
        index_and_source = {}
        for iw in ("IW1", "IW2", "IW3"):
            start_bursts, end_bursts, source = self.get_bursts_and_source(
                iw.lower()
            )  # 获取此 subswath 的起止编号和此 subswath 需要的影像数据。
            if not (start_bursts and end_bursts):
                index_and_source[iw] = {"first_burst_index": 0, "last_burst_index": 0, "source": ()}
                continue
            start_burst, end_burst = max(start_bursts), sum(
                end_bursts
            )  # start_bursts 中的最大值为该 subswath 的起始编号，end_bursts 中的最小值为终止编号。
            index_and_source[iw] = {
                "first_burst_index": start_burst,
                "last_burst_index": end_burst,
                "source": source,
            }
        return index_and_source
