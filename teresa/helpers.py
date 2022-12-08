from __future__ import annotations
import glob
import json
import os
import re
import shapely.wkt
import sys
import subprocess
import tempfile

import geojson
import requests
import logging
import zipfile
import numpy as np
from lxml import etree
from typing import TYPE_CHECKING

from shapely.geometry import shape, Polygon
from urllib.parse import quote
from pypinyin import lazy_pinyin as pinyin

logger = logging.getLogger("sLogger")

API_KEY = "B5EBZ-W2GCI-Q23GO-5RJTM-YRZL7-WJBHO"

if TYPE_CHECKING:
    from teresa.stack import Sentinel1SlcImage

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


class BurstsUtilities:
    """:class: `BurstsUtilities` 计算 :class: `Sentinel1SlcImage` 对象需要的 source，subswath 以及 burst 的起止编号。
    在初始化阶段，提取 Sentinel1SlcImage 对象所需的所有 xml 文件，同时将输入的 aoi 转为 Polygon 对象。

    Parameters
    ----------
    slc_image : Sentinel1SlcImage
    aoi: str
        Geojson 或字符串格式的 AOI，字符串形式如："POLYGON (...)"

    Attributes
    ----------
    slc_image : Sentinel1SlcImage
    aoi : str
        Geojson 或字符串格式的 AOI，字符串形式如："POLYGON (...)"
    xml_info : dict
        读取一个 xml 文件中所需的信息，存放到 self.xml_info 中。该字典记录某单景影像的单个 subswath 的
        burst 数量、单 burst 的行数。同时存有一个 np.array 格式的数组 points_info。该数组第一行至第四
        行依次是该 subswath 中某些点的：行坐标，列坐标，经度，纬度。其每一列是一一对应的关系，这样可以使用
        矩阵固定它们之间的关系。下面给出 points_info 的样例。

    Example
    --------
    >>>print(self.xml_info["points_info"])
    np.array([
        [0, 0, 0, 1, 2, 3, ...],
        [0, 0, 0, 7, 9, 9, ...],
        [103.11, 103.22, ...],
        [23.1, 23.2, 23.3, ...]
    ])

    """

    def __init__(self, slc_image: Sentinel1SlcImage, aoi: str):
        self.slc_image = slc_image
        # manifest_dir 为 slc_image 对象所需的所有影像的源文件的存储路径，如: /data/slc/Chengdu/20210101/
        self.manifest_dir = os.path.join(slc_image.sourcedir, slc_image.date)
        self._extract_meta()  # 将 SlcImage 中三个条带对应的文件解压
        # 将 aoi 转为 polygon，可以是 polygon 字符串或 geojson 文件
        self.aoi = PolygonFactory.generate_polygon(aoi)

    def _extract_meta(self):
        """提取输入对象中 source 属性下的所有 zip 文件的源文件，存放在工作目录下对应日期的目录。比如某个
        :class: `Sentinel1SlcImage` 对应的日期为 20210101，所有 zip 文件的存放目录为 /home/jerry/test,
        则提取出的文件存放路径为: /home/jerry/test/20210101/1.SAFE，此时该 SAFE 文件内部数据的存放结构与原始
        数据一致，但不包括影像数据。
        """

        def _unzip(fzip: str) -> None:
            """提取一景 zip 文件的源文件。"""
            try:
                with zipfile.ZipFile(fzip, "r") as zipfp:
                    zip_file = zipfile.ZipFile(fzip)
                    for fxml in zip_file.namelist():
                        if re.match(r"(.*)/annotation/(s1.*vv.*)", fxml):
                            zip_file.extract(fxml, self.manifest_dir)
            except zipfile.BadZipFile:
                logger.error(f"{fzip} 文件损坏")
                sys.exit()  # 解压错误就中止程序
            except PermissionError:
                logger.error(f"{self.manifest_dir} 没有写出权限")
                sys.exit()

        # 将该 Sentinel1SlcImage 对象 source 属性中的所有 zip 文件的 xml 文件提取。
        # 三个条带对应的 source 文件可能相同也可能不同
        unzipped = ()
        for subswath in ("IW1", "IW2", "IW3"):
            fzips = getattr(self.slc_image, subswath)["source"]
            for fzip in fzips:
                # 三个 subswath 可能存在数据重复的情况，如果已解压过则跳过
                if fzip not in unzipped:
                    _unzip(fzip)
                    unzipped += (fzip,)

    def _read_xml(self, fxml: str):
        """将 xml 文件中的信息存储到字典中。"""
        xml = etree.parse(fxml, etree.XMLParser())
        line_per_burst, number_of_lines = (
            int(xml.xpath("//linesPerBurst/text()")[0]),
            int(xml.xpath("//numberOfLines/text()")[0]),
        )
        lines, pixels = (
            list(map(int, xml.xpath("//line/text()"))),
            list(map(int, xml.xpath("//pixel/text()"))),
        )
        longitudes, latitudes = (
            list(map(float, xml.xpath("//longitude/text()"))),
            list(map(float, xml.xpath("//latitude/text()"))),
        )
        points_info = np.array([lines, pixels, longitudes, latitudes])
        number_of_bursts = number_of_lines // line_per_burst
        self.xml_info = {
            "points_info": points_info,
            "lines_per_burst": line_per_burst,
            "number_of_burts": number_of_bursts,
        }

    def find_burst_in_overlap(self, overlap: Polygon) -> int:
        """根据 points_info 中记录的行号、经度和纬度信息，建立一个映射公式，其中输入值为经度和纬度，输出值为行号。此方法
        已经过实验论证，三者几乎呈转线性关系，转换后的行坐标精度在几十个像素以内，完全可以确保后续计算的准确性。

        Parameter
        ---------
        overlap : Polygon
            AOI 与某个 subswath 的相交区域。

        Returns
        -------
        burst_start : int
            burst 起始编号
        burst_end : int
            burst 截止编号

        """

        points_info, lines_per_burst, number_of_burts = (
            self.xml_info["points_info"],
            self.xml_info["lines_per_burst"],
            self.xml_info["number_of_burts"],
        )
        lonlat = points_info[2:4].T  # numpy 线性拟合需要参数以列排列，将行转秩
        # 增加一个单位向量作为常数项
        coefficient = np.concatenate((np.ones((lonlat.shape[0], 1)), lonlat), axis=1)
        w0, w1, w2 = np.linalg.lstsq(coefficient, points_info[0], rcond=None)[0]  # 计算出三个参数
        coordinates = list(overlap.exterior.coords)  # 将相交区域的范围转为坐标列表
        bursts = []
        for lon, lat in coordinates:  # 计算每一个坐标对应的 burst 编号
            line = w0 + w1 * lon + w2 * lat
            burst_number = int(line) // lines_per_burst + 1
            if burst_number < 1:
                burst_number = 1
            elif burst_number > number_of_burts:
                burst_number = number_of_burts
            bursts.append(burst_number)
            burst_start, burst_end = min(bursts), max(bursts)
        return burst_start, burst_end

    def _xml2polygon(self, fxml: str) -> Polygon:
        """将单个 xml 文件转化为其对应的范围 Polygon。"""
        self._read_xml(fxml)  # 此时 self.xml_info 已初始化成对应 subswath 的信息
        points_info = self.xml_info["points_info"]
        # 当行坐标为0 或 最大时，对应的该 subswath 的上下两个边界
        # 当列坐标为 0 或最大时，对应的该 subswath 的左右两个边界
        upper_bound, lower_bound, left_bound, right_bound = map(
            lambda x, y: np.where(points_info[x] == y),
            [0, 0, 1, 1],
            [0, np.max(points_info[0]), 0, np.max(points_info[1])],
        )
        # 更加优雅的方式获取该 subswath 四个角的坐标。以左上角点为例，其行号和列号满足同时为 0，根据 points_info 中
        # 一一对应的关系，获取该角点的经纬度。
        upper_left, upper_right, lower_right, lower_left = map(
            lambda x, y: points_info[2:4, np.intersect1d(x, y)].T.tolist()[0],
            [upper_bound, upper_bound, lower_bound, lower_bound],
            [left_bound, right_bound, right_bound, left_bound],
        )
        corners = [upper_left, upper_right, lower_right, lower_left, upper_left]

        return Polygon(corners)  # 根据四个角生成对应范围的 Polygon

    def get_bursts_and_source(self, iw: str) -> tuple:
        """计算某一个 subswath 的起止编号以及其所需的 source 文件。

        Parameter
        ---------
        iw : str
            条带编号，值只可能是 "iw1", "iw2", "iw3" 其中一个。

        Returns
        -------
        start_bursts: tuple of int
            记录起始 burst 编号的元组。
        end_bursts : tuple of int
            记录终止 burst 编号的元组。
        source : tuple of string
            记录该条带所需数据的元组。

        Example
        -------
        start_bursts, end_bursts 和 source 为一一对应的关系。下面的示例表示：aoi 与 iw1 条带的交集为
        1.zip 影像对应该条带的 4 到 9 burst 和 2.zip 影像对应该条带的 1 到 3 burst。
        >>>iw
        "iw1"
        >>>start_bursts
        (4, 1)
        >>>end_bursts
        (9, 3)
        >>>source
        ("1.zip", "2.zip")


        """

        source, start_bursts, end_bursts = (), (), ()
        # meta_dir 为该 Sentinel1SlcImage 对象对应头文件的目录
        manifest_dir = self.manifest_dir
        for safe_file in os.listdir(manifest_dir):
            # 某一个文件不带后缀的文件名，因为原始数据为 *.zip，safe_file 为 *.SAFE。
            fname = safe_file.split(".")[0]
            xml_dir = os.path.join(manifest_dir, safe_file, "annotation")  # 该文件 xml 数据存放的具体路径
            xml_path = glob.glob(os.path.join(xml_dir, f"s1*{iw}*"))[0]  # 该文件中对应该 IW 的 xml 的文件路径。
            subswath_boundary = self._xml2polygon(xml_path)  # 将此 xml 文件转换成范围 Polygon
            # 判断此 Polygon 是否与 AOI 相交，如相交返回 polygon 类的相交区域，否则返回 None。
            overlapped = (
                None
                if subswath_boundary.intersection(self.aoi).is_empty
                else subswath_boundary.intersection(self.aoi)
            )
            # 如果不相交，则继续下一个 SAFE file。如果三个条带与 AOI 都不相交，则此时 source, bursts_start,
            # bursts_end 都为空元组。
            if not overlapped:
                continue
            zip_path = os.path.join(os.path.dirname(manifest_dir), fname + ".zip")
            source += (zip_path,)
            # 计算相交区域在该 subswath 对应的起止编号。
            burst_start, burst_end = self.find_burst_in_overlap(overlapped)
            # 起始 burst 往影像上方扩大一个 burst，如果计算出的起始 burst 编号为 1，则取 1。
            start_bursts += (max(burst_start - 1, 1),)
            # 终止 burst 往影像下方扩大一个 burst，如果计算出的终止编号为 9，则取 9。
            end_bursts += (min(burst_end + 1, 9),)  # TODO 将 9 替换成该 subswath 的真实 burst 数。
        return start_bursts, end_bursts, source

    def get_minimum_overlapping(self) -> dict:
        """此函数为 crop 的接口函数，逐条带计算所需的 source 文件以及起止 burst 编号，返回
        index_and_source 字典。

        Return
        ------
        index_and_source : dict
            字典的 key 值为 subwath 编号，为 IW1，IW2，IW3。value 值为每个条带对应的起始
            burst 编号和终止 burst 编号，以及其所需的 zip 文件。以 iw1 条带为例如下所示。

        Example
        -------
        假设 iw1 条带需要两景影像：1.zip 和 2.zip。在 1.zip 影像中对应的 burst 起止编号为 5-9，在 2.zip 中
        对应的 burst 的起止编号为 1-3。
        >>>index_and_source["IW1"]
        {
            "first_burst_index": 5,
            "last_burst_index": 12,
            "source": (../1.zip, ../2.zip)
        }
        如果 AOI 与 iw1 条带不相交。
        >>>index_and_source["IW1"]
        {
            "first_burst_index": 0,
            "last_burst_index": 0,
            "source": ()
        }

        """

        index_and_source = {}
        for iw in ("IW1", "IW2", "IW3"):
            # 获取此 subswath 的起止编号和此 subswath 需要的影像数据。start_bursts、end_bursts
            # 和 source 是元组类型的数据，这三个元组中的元素一一对应。
            start_bursts, end_bursts, source = self.get_bursts_and_source(iw.lower())
            # 当这两个元组为空时，说明 AOI 与该条带不相交，同时 source 也为空数组。在 coregister
            # 中，若 source 为空，则会直接跳过该条带。
            if not (start_bursts and end_bursts):
                index_and_source[iw] = {
                    "first_burst_index": 0,
                    "last_burst_index": 0,
                    "source": (),
                }
                continue
            # slice assembly 后的起始 burst 编号总是 start_bursts 中的最大值，因为下方的
            # subswath 起始 burst 编号总是为 1；终止编号为 end_bursts 中数字的和，具体可理解此
            # function 中的例子。
            start_burst, end_burst = max(start_bursts), sum(end_bursts)
            index_and_source[iw] = {
                "first_burst_index": start_burst,
                "last_burst_index": end_burst,
                "source": source,
            }
        return index_and_source


class PolygonFactory:
    @staticmethod
    def generate_polygon(input_aoi) -> Polygon:
        """生产 aoi 的 Polygon 对象，支持的输入数据类型有 QGIS、geojson.io 生成的 geojson 文件，POLYGON
        字符串。

        Parameter
        ---------
        input_aoi : str
            geojson 文件的路径，或是 Polygon 字符串，如：'POLYGON((....))'。

        Return
        ------
        AOI 的 Polygon 对象。
        """
        # 首先判断是不是 POLYGON 字符串。
        if input_aoi.startswith("POLYGON"):
            aoi = shapely.wkt.loads(input_aoi)
            return aoi
        # 如果不是 POLYGON 字符串，而且文件不存在，则报错。
        if not os.path.exists(input_aoi):
            raise RuntimeError(f"{input_aoi} 文件不存在。")

        with open(input_aoi, "r") as gf:
            context = json.load(gf)
        if context["type"] == "Polygon":
            return shape(context)
        else:
            return shape(context["features"][0]["geometry"])


class QueryS1Data:
    """:class: `QueryS1Data` 根据起止时间、AOI 查询影像，将查询结果记录到 txt 文件，并以 Path 和 Frame 对
    影像进行分类。该功能是连接到 ASF 实现，确保您的电脑可以正常访问 ASF 网站。

    Parameters
    ---------
    aoi : str
        输入的 AOI，可以是字符串，也可以是 geojson 文件，目前支持 QGIS 和 geojson.io 生成的 geojson 文件。
    start_time : str
        影像的起始日期，格式为 yyyy-mm-dd，例如: 2021-12-12。
    end_time : str
        影像的截止日期，格式为 yyyy-mm-dd，例如: 2021-12-12。

    Attributes
    ----------
    aoi : Polygon
        查询范围的 Polygon 对象。
    start_time : str
        影像的起始日期，格式为 yyyy-mm-dd，例如: 2021-12-12。
    end_time : str
        影像的截止日期，格式为 yyyy-mm-dd，例如: 2021-12-12。
    dataset : list
        获取的原始数据信息，包含所有与 AOI 相交的影像。列表的格式存储，每一景影像的信息以字典的格式存储。
    processed: dict
        排序整理后的影像信息，以字典的形式存储。

    Examples
    --------
    >>>query_object = QueryS1Data(
        aoi="POLYGON((118.1262 35.118,119.4696 35.118,119.4696 36.4281,118.1262 36.4281,118.1262 35.118))",
        start_time="2022-11-01",
        end_time="2022-11-30",
    )
    >>>query_object.query()
    >>>print(self.processed)
    {
        'COVER': {}, 
        'INTERSECT': {
            '69': {
            '109': 
            ['S1A_IW_SLC__1SDV_20210106T100412_20210106T100439_036016_043851_8CFC.zip'], 
            '104': 
            ['S1A_IW_SLC__1SDV_20210106T100347_20210106T100414_036016_043851_8FF5.zip']}}
            }
    >>>print(self.dataset)
    [
        {'absoluteOrbit': '41150', 'beamMode': 'IW', 'beamModeType': 'IW',
        'beamSwath': None, 'browse': None, 'catSceneId': None, 
        'centerLat': '31.8168', 'centerLon': '103.1332',
        'collectionName': None, 'doppler': '0', 
        'downloadUrl': 'https://datapool.asf.alaska.edu/SLC/\
        SA/S1A_IW_SLC__1SDV_20211224T110920_20211224T110947_041150_04E3B8_295D.zip'},
        ....]
    将最终的查询结果存储到一个 txt 文件。
    >>>query_object.query().serialize("/home/result.txt")
    >>>vi /home/result.txt
    full_coverage
    partial_coverage
    TRACK: 171
    FRAME: 116
    ----------------------------------------------------------------------
    S1A_IW_SLC__1SDV_20221128T095647_20221128T095715_046093_05846C_6907.zip
    S1A_IW_SLC__1SDV_20221116T095648_20221116T095715_045918_057E84_F6F9.zip
    S1A_IW_SLC__1SDV_20221104T095648_20221104T095716_045743_057892_B368.zip
    ----------------------------------------------------------------------
    FRAME: 111
    ----------------------------------------------------------------------
    S1A_IW_SLC__1SDV_20221128T095623_20221128T095650_046093_05846C_A1F6.zip
    S1A_IW_SLC__1SDV_20221116T095623_20221116T095650_045918_057E84_91BE.zip
    S1A_IW_SLC__1SDV_20221104T095623_20221104T095650_045743_057892_E1AB.zip
    ----------------------------------------------------------------------
    .....
    """

    def __init__(self, aoi: str, start_time: str, end_time: str) -> None:
        self.start_time = start_time
        self.end_time = end_time
        self.aoi = PolygonFactory.generate_polygon(aoi)
        self.processed = {"full_coverage": {}, "partial_coverage": {}}
        self.dataset = None

    def query(self):
        """从 ASF 网址获取所需的 S1 影像信息，并将获取的数据进行分类。"""
        self._acquire()  # 查询并将获取的信息存储到 self.information 中
        self._process()  # 将获取的原始数据按照规则排序。
        return self

    def serialize(self, output_path: str) -> None:
        """将分类好的数据写出到一个 txt 文件。"""
        with open(output_path, "w") as f:
            for coverage, tracks in self.processed.items():
                # 层层遍历，先写入位置关系。
                f.write(coverage + "\n")
                for track, frames in tracks.items():
                    # 再写入 TRACK。
                    f.write("TRACK: " + track + "\n")
                    for frame, s1s in frames.items():
                        # 再写入 frame_number。
                        f.write("FRAME: {}\n".format(frame))
                        f.write(
                            "----------------------------------------------------------------------\n"
                        )
                        for s1 in s1s:
                            # 写入影像名称。
                            f.write(s1 + "\n")
                        f.write(
                            "----------------------------------------------------------------------\n"
                        )

    def _acquire(self):
        """从 ASF 网站上获取原始未经处理的数据。"""
        # 建立一个 json 格式的临时文件，接受查询获取的数据，使用完后自动删除。
        tp = tempfile.NamedTemporaryFile(suffix=".json", mode="w")
        # 将 polygon 字符串转码使其能被 ASF 服务器识别。
        encoded_polygon = quote(self.aoi.wkt).replace("%20", "+").replace("%2C", ",")
        # 基于起止时间，aoi，输出的文件路径定义查询命令。
        cmd = (
            r"curl https://api.daac.asf.alaska.edu/services/search/param?"
            + r"platform=S1\&beamMode=IW\&processingLevel=SLC\&output=JSON"
            + r"\&start={}\&end={}\&intersectsWith={} > {}".format(
                self.start_time, self.end_time, encoded_polygon, tp.name
            )
        )

        status, output = subprocess.getstatusoutput(cmd)

        if status != 0:
            raise SystemExit(f"查询时出错，具体报错原因下: {output}")
        with open(tp.name) as jf:
            try:
                self.dataset = json.load(jf)[0]
            # 参数错误时，查询出的数据打开会错误。
            except:
                raise SystemExit("网络连接正确，查询时参数错误。")
        tp.close()

    def _check_full_or_partial_coverage(self, boundary: str) -> str:
        """
        判断 aoi 与某景影像的位置关系，相交还是覆盖。ASF 官网的查询逻辑排除了与 aoi 相离的影像。

        Parameter
        ---------
        boundary : str
            S1 影像范围的 polygon 字符串，如 'POLYGON((...))'
        """
        s1_boundary = PolygonFactory.generate_polygon(boundary)  # 使用工厂将 boundary 转为 Polygon。
        # aoi 与某景影像的相交面积与 aoi 面积的比值。当值大于 0.99 时，认为该影像覆盖 aoi，否则认为两者是相交关系。
        intersection_percent = float(self.aoi.intersection(s1_boundary).area) / float(self.aoi.area)
        return "full_coverage" if intersection_percent >= 0.99 else "partial_coverage"

    def _process(self):
        """将获取的原始信息整理，按照相对位置关系，track，frame 的关系整理排序。"""
        for data in self.dataset:
            track, frame_number, fname, boundary = (
                data["track"],
                data["frameNumber"],
                data["fileName"],
                data["stringFootprint"],
            )
            # 判断此 boundary 与 self.aoi 的位置关系。
            coverage = self._check_full_or_partial_coverage(boundary)
            # 此处的代码怎么看起来都不是很美观，但目前为止我只能想到这个方法来实现
            # 当某个影像的 track 在 self.processed 中没有出现过，以此 track 为 key 值创建
            # 一个空字典。
            if track not in self.processed[coverage]:
                self.processed[coverage][track] = {}
            # 当某个影像的 frame 在 self.processed 相应的 track 字典中没有出现过，以此 frame
            # 为 key 值在该 track 字典中创建一个空列表。
            if frame_number not in self.processed[coverage][track]:
                self.processed[coverage][track][frame_number] = []
            # 基于位置关系、track 和 frame_number 找到相应的列表，将该文件名添加到列表中。
            self.processed[coverage][track][frame_number].append(fname)
