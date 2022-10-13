import os
import re
import glob
import shapely.wkt
import sys

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
    """FindBursts 计算 Sentinel1SlcImage 对象的需要的 source 以及起止编号。

    参数
    ---
    slc_image : Sentinel1SlcImage
        Sentinel1SlcImage 类的对象
    aoi: str
        Geojson 或字符串格式的 AOI，字符串形式如："POLYGON (...)"

    例子
    ---
    slc_image :
        输入的 slc_image 已经初始化 IW1, IW2, IW3 属性，以 IW1 属性为例，其初始化后的格式为
        {"first_burst_index": 1, "last_burst_index": 999,"fmeta": self.source}, 计算后属性变为
        {"first_burst_index": 2, "last_burst_index": 8,"fmeta": (source_iw)}，其中的 source_iw 为 IW1
        条带所需的所有数据。
    """

    def __init__(self, slc_image, aoi: str):  # TODO 如何定义 slc_image 的 Typehint。
        """在对象初始化阶段，提取该 Sentinel1SlcImage 对象所需的所有 xml 文件，以及将 AOI 转为 polygon 对象。"""
        self.slc_image = slc_image
        self.meta_sourcedir = os.path.join(slc_image.sourcedir, slc_image.date)
        self._extract_meta()  # 将 SlcImage 中三个条带对应的文件解压
        self.aoi = self._other2polygon(aoi)  # 将 aoi 转为 polygon，可以是 polygon 字符串或 geojson 文件

    def _extract_meta(self):
        """提取输入对象中 source 属性下的所有 zip 文件的源文件，存放在工作目录下对应日期的目录下面。
        比如 某个 Sentinel1SlcImage 对应的日期为 20210101，所有 zip 文件的存放目录为 /home/jerry/test,
        则提取出的文件存放路径为: /home/jerry/test/20210101/1.SAFE，此时该 SAFE 文件内部数据的存放结构与原始
        数据一致，但不包括影像数据。
        """

        def _unzip(fzip: str) -> None:
            # 将一景 zip 格式的文件中的 xml 文件提取到目标目录。
            try:
                zip_file = zipfile.ZipFile(fzip)
            except:
                logger.error(f"{fzip} wrong")
                sys.exit()  # 解压错误就中止程序
            for fxml in zip_file.namelist():
                re_matched = re.match(r"(.*)/annotation/(s1.*vv.*)", fxml)
                if not re_matched:
                    continue
                zip_file.extract(fxml, self.meta_sourcedir)

        # 将该 Sentinel1SlcImage 对象 source 属性中的所有 zip 文件的 xml 文件提取。
        # 三个条带对应的 source 文件可能相同也可能不同
        unzipped = ()
        for subswath in ("IW1", "IW2", "IW3"):
            fzips = getattr(self.slc_image, subswath)["source"]
            for fzip in fzips:
                if fzip not in unzipped:  # 当某个文件已经解压过时，跳过
                    _unzip(fzip)
                    unzipped += (fzip,)

    def _other2polygon(self, aoi_or_geojson: str) -> Polygon:
        """将 geojson 格式的文件转为 polygon 对象"""
        if not os.path.isfile(aoi_or_geojson):  # 发现实际使用时直接使用 ASF 的 Polygon 字符串更方便些，增加一个数据类型接口。
            boundary = shapely.wkt.loads(aoi_or_geojson)
            return boundary

        with open(aoi_or_geojson) as f:
            geojson_context = geojson.load(f)
        try:  # 不同方式建立的 geojson 文件格式可能会不同
            boundary = shape(geojson_context["features"][0]["geometry"])
        except:
            boundary = shape(geojson_context)
        return boundary

    def _read_xml(self, fxml: str):
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

    def find_burst_in_overlap(self, overlap: Polygon) -> int:
        """计算相交区域在对应 subswath 中对应的起止编号

        参数
        ---
        points_info : np.array
            一个 4*N 纬度数组，第一行为行坐标，第二行为列坐标，第三行为经度，第四行为纬度
        lines_per_burst : int
            burst 对应的行数
        burst_number : int
            此条带的 burst 数

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
        lonlat = points_info[2:4].T  # numpy 线性拟合需要参数以列排列，将行转秩
        coefficient = np.concatenate(
            (np.ones((lonlat.shape[0], 1)), lonlat), axis=1
        )  # 增加一个单位向量作为常数项
        w0, w1, w2 = np.linalg.lstsq(coefficient, points_info[0], rcond=None)[0]  # 计算出三个参数
        coordinates = list(overlap.exterior.coords)  # 将相交区域的范围转为坐标列表
        bursts = []
        for lon, lat in coordinates:  # 计算每一个坐标对应的 burst 编号
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
        self._read_xml(fxml)  # 此时 self.xml_info 已初始化成对应 subswath 的信息
        points_info = self.xml_info["points_info"]
        # 当行坐标为0 或 最大时，对应的该 subswath 的上下两个边界
        # 当列坐标为 0 或最大时，对应的该 subswath 的左右两个边界
        up_index = np.where(points_info[0] == 0)
        low_index = np.where(points_info[0] == np.max(points_info[0]))
        left_index = np.where(points_info[1] == 0)
        right_index = np.where(points_info[1] == np.max(points_info[1]))
        # 获取该 subswath 四个角的坐标
        left_up = points_info[2:4, np.intersect1d(up_index, left_index)].tolist()
        right_up = points_info[2:4, np.intersect1d(up_index, right_index)].tolist()
        right_low = points_info[2:4, np.intersect1d(low_index, right_index)].tolist()
        left_low = points_info[2:4, np.intersect1d(low_index, left_index)].tolist()
        coordinates = []
        for corner in (left_up, right_up, right_low, left_low, left_up):
            coordinates.append([corner[0][0], corner[1][0]])
        xml_boundary = Polygon(coordinates)  # 根据四个角生成对应范围的 Polygon
        return xml_boundary

    def get_bursts_and_source(self, iw: str) -> tuple:
        """计算某一个 iw 的起止编号以及 source 文件。"""
        source, bursts_start, bursts_end = (), (), ()
        meta_dir = self.meta_sourcedir  # meta_dir 为该 Sentinel1SlcImage 对象对应头文件的目录
        for safe_file in os.listdir(meta_dir):
            fname = safe_file.split(".")[0]  # 某一个文件不带后缀的文件名，因为原始数据为 *.zip，safe_file 为 *.SAFE。
            xml_dir = os.path.join(meta_dir, safe_file, "annotation")  # 该文件 xml 数据存放的具体路径
            xml_path = glob.glob(os.path.join(xml_dir, f"s1*{iw}*"))[0]  # 该文件中对应某个 xml 的文件路径。
            subswath_boundary = self.xml2polygon(xml_path)  # 将此 xml 文件转换成范围 Polygon
            overlapping_boundary = (
                None
                if subswath_boundary.intersection(self.aoi).is_empty
                else subswath_boundary.intersection(self.aoi)
            )  # 判断此 Polygon 是否与 AOI 相交，如相交返回 polygon 类的相交区域，否则返回 None。
            if not overlapping_boundary:
                continue
            # 如果不相交，则继续下一个 SAFE file。如果三个条带与 AOI 都不相交，则此时 source,bursts_start,bursts_end 都为空元组。
            zip_path = os.path.join(os.path.dirname(meta_dir), fname + ".zip")
            source += (zip_path,)
            burst_start, burst_end = self.find_burst_in_overlap(
                overlapping_boundary
            )  # 计算相交区域在该 subswath 对应的起止编号。
            bursts_start += (max(burst_start - 1, 1),)
            bursts_end += (min(burst_end + 1, 9),)  # 扩大一个 burst
        return bursts_start, bursts_end, source

    def get_minimum_overlapping(self) -> dict:
        """此函数为 crop 的接口函数，逐条带计算所需的 source 文件以及起止 burst 编号

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
            start_bursts, end_bursts, source = self.get_bursts_and_source(iw.lower())
            # 获取此 subswath 的起止编号和此 subswath 需要的影像数据。注意此时返回的 start_bursts、end_bursts 和 source 是元组类型的数据，
            # 这三个元组存在一一对应的关系，例如 (3,1),(9,3),(1.zip,2.zip) 对应上面三个数据，则表明的意思是在该条带上，1.zip 数据的起止 burst
            # 编号为 3，9，2.zip 数据的起止编号为 1,3。
            if not (
                start_bursts and end_bursts
            ):  # 当这两个元组为空时，说明 AOI 与该条带不相交，具体逻辑在 get_bursts_and_source 中。
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
