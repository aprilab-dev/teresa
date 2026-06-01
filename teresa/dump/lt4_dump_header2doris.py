

import os
import numpy as np
from xml.etree import ElementTree
from datetime import datetime
from contextlib import redirect_stdout

SPEED_OF_LIGHT = 299792458

def hms2sec(timestr: str, convertFlag: str = "int") -> float:
    """Convert time string to seconds"""
    time_parts = timestr.split(' ')[1].split(':')
    secString = (
        int(time_parts[0]) * 3600
        + int(time_parts[1]) * 60
        + float(time_parts[2])
    )
    if convertFlag == "int":
        return secString
    elif convertFlag == "float":
        return secString
    else:
        return round(secString)

def extract_lt4_meta(source_meta_path):
    """提取 LT4 参数并进行单位换算，以适配 Doris 格式"""
    meta = {}

    tree = ElementTree.parse(source_meta_path)
    root = tree.getroot()

    # --- 基础文件信息 ---
    satellite = root.findtext("satellite")

    #! 这里先这样，后续搜索同路径下的 tiff 文件名
    meta["Datafile"] = source_meta_path
    meta["Radar_wavelength (m)"] = root.findtext("sensor/lamda")

    meta["Volume file"] = source_meta_path
    meta["Volume_ID"] = root.findtext("sceneID")
    meta["Volume_set_identifier"] = (root.findtext("satellite") + "_" +root.findtext("orbitID"))

    meta["Xtrack_f_DC_constant (Hz, early edge)"] = (root.findtext("processinfo/DopplerCentroidCoefficients/d0"))
    meta["Xtrack_f_DC_linear (Hz/s, early edge)"] = (root.findtext("processinfo/DopplerCentroidCoefficients/d1"))
    meta["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"] = (root.findtext("processinfo/DopplerCentroidCoefficients/d2"))

    # mission info
    meta["(Check)Number of records in ref. file"] = root.findtext("productinfo/imageinfo/height")
    meta["(Check)Number of records in ref. file"] = int(root.findtext("imageinfo/height"))
    meta["SAR_PROCESSOR"] = (root.findtext("satellite") + "_" + root.findtext("processinfo/algorithm"))
    meta["Product type specifier"] = root.findtext("productinfo/productType")
    meta["Logical volume generating facility"] = root.findtext("Station")
    meta["Logical volume creation date"] = root.findtext("productinfo/productGentime")
    meta["Location and date/time of product creation"] = (root.findtext("Station") + " " +root.findtext("productinfo/productGentime"))

    meta["Orbit"] = root.findtext("orbitID")
    meta["Direction"] = root.findtext("Direction")
    meta["Mode"] = root.findtext("sensor/imagingMode")

    meta["Leader file"] = source_meta_path
    meta["Sensor platform mission identifer"] = root.findtext("satellite")

    meta["Scene_centre_longitude"] = root.findtext("imageinfo/center/longitude")
    meta["Scene_centre_latitude"] = root.findtext("imageinfo/center/latitude")

    lat = root.findtext("imageinfo/center/latitude")
    lon = root.findtext("imageinfo/center/longitude")
    meta["Scene location"] = (f"lat: {lat} lon: {lon}")

    orbit_id = root.findtext("orbitID")
    direction = root.findtext("Direction")
    mode = root.findtext("sensor/imagingMode")
    meta["Scene identification"] = (
        f"Orbit: {orbit_id} "
        f"{direction} "
        f"Mode: {mode}"
    )

    # product info
    meta["Radar_wavelength (m)"] = root.findtext("sensor/lamda")
    meta["First_pixel_azimuth_time (UTC)"] = root.findtext("imageinfo/imagingTime/start")
    meta["Last_pixel_azimuth_time (UTC)"] = root.findtext("imageinfo/imagingTime/end")
    
    PRF = float(root.findtext("sensor/waveParams/wave/PRF"))
    meta["Pulse_Repetition_Frequency (computed, Hz)"] = PRF
    meta["Total_azimuth_band_width (Hz)"] = float(root.findtext("processinfo/AzimuthLookBandWidth")) * PRF / (2 * np.pi)

    near_range = float(root.findtext("imageinfo/nearRange"))
    meta["Range_time_to_first_pixel (2way) (ms)"] = (2 * near_range / SPEED_OF_LIGHT) * 1000
    meta["Range_sampling_rate (computed, MHz)"] = float(root.findtext("sensor/waveParams/wave/sampleRate"))
    meta["Total_range_band_width (MHz)"] = float(root.findtext("processinfo/RangeLookBandWidth")) / 1e6

    # slc info
    meta["Dataformat"] = root.findtext("productinfo/productFormat")
    meta["Number_of_lines_original"] = int(root.findtext("imageinfo/width"))
    meta["Number_of_pixels_original"] = int(root.findtext("imageinfo/height"))

    # orbit info
    gps_points = root.findall("GPS/GPSParam")
    meta["Orbit_n_pts"] = len(gps_points)

    gps_list = root.findall("GPS/GPSParam")
    meta["Orbit_n_pts"] = len(gps_list)
    meta["Orbit_Time"] = []
    meta["Orbit_X"] = []
    meta["Orbit_Y"] = []
    meta["Orbit_Z"] = []
    meta["Orbit_VX"] = []
    meta["Orbit_VY"] = []
    meta["Orbit_VZ"] = []

    for gps in gps_list:
        meta["Orbit_Time"].append(gps.findtext("TimeStamp"))
        meta["Orbit_X"].append(float(gps.findtext("xPosition")))
        meta["Orbit_Y"].append(float(gps.findtext("yPosition")))
        meta["Orbit_Z"].append(float(gps.findtext("zPosition")))
        meta["Orbit_VX"].append(float(gps.findtext("xVelocitye")))
        meta["Orbit_VY"].append(float(gps.findtext("yVelocitye")))
        meta["Orbit_VZ"].append(float(gps.findtext("zVelocitye")))

    
    # 轨道排序去重（严格递增）- 以 Orbit_Time 为主键，其他字段保持一致排序和去重
    keys = [
        "Orbit_Time",
        "Orbit_X",
        "Orbit_Y",
        "Orbit_Z",
        "Orbit_VX",
        "Orbit_VY",
        "Orbit_VZ"
    ]

    # 打包
    orbit_data = list(zip(*(meta[k] for k in keys)))

    # 排序
    orbit_data.sort(
        key=lambda x: datetime.strptime(
            x[0],
            "%Y-%m-%d %H:%M:%S.%f"
        )
    )

    # 去重（严格递增）
    filtered_data = []

    last_time = None

    for row in orbit_data:

        current_time = datetime.strptime(
            row[0],
            "%Y-%m-%d %H:%M:%S.%f"
        )

        if last_time is None or current_time > last_time:
            filtered_data.append(row)
            last_time = current_time

    # 解包回 meta
    for i, k in enumerate(keys):
        meta[k] = [row[i] for row in filtered_data]

    meta["Orbit_n_pts"] = len(filtered_data)

    return meta

def write_res_file(meta):
    """将字典输出为 Doris 识别的文本格式"""
    
    # --- 1. 打印 Doris 必须的起始信息和流程控制记分牌 ---
    print("===========================================================")
    print("           TERESA - 国产卫星 SAR 图像配准工具 (v0.1)           ")
    print("===========================================================")
    print("File Generated  : ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("File Type       : SAR Registration Metadata")
    print("Input Mission   : LT4")
    print("-----------------------------------------------------------")
    print("")
    print("**************************************************************")
    print("*Processing_Status_Flag:")
    print("**************************************************************")
    print("Start_process_control")
    print("readfiles:\t\t1")
    print("precise_orbits:\t\t0")
    print("modify_orbits:\t\t0")
    print("crop:\t\t0")     # 此处留 0，csk_dump_data 会将其替换为 1
    print("sim_amplitude:\t\t0")
    print("master_timing:\t\t0")
    print("oversample:\t\t0")
    print("resample:\t\t0")
    print("filt_azi:\t\t0")
    print("filt_range:\t\t0")
    print("NOT_USED:\t\t0")
    print("End_process_control")
    print("")
    print("-----------------------------------------------------------")

    # --- 2. 严格对齐 BC 字典的键值顺序 ---
    keys_lead = (
        "Volume file",
        "Volume_ID",
        "Volume_set_identifier",
        "(Check)Number of records in ref. file",
        "SAR_PROCESSOR",
        "Product type specifier",
        "Logical volume generating facility",
        "Logical volume creation date",
        "Location and date/time of product creation",
        "Scene identification",
        "Scene location",
        "Leader file",
        "Sensor platform mission identifer",
        "Scene_centre_latitude",
        "Scene_centre_longitude",
        "Radar_wavelength (m)",
        "First_pixel_azimuth_time (UTC)",
        "Pulse_Repetition_Frequency (computed, Hz)",
        "Total_azimuth_band_width (Hz)",
        "Weighting_azimuth",
        "Xtrack_f_DC_constant (Hz, early edge)",
        "Xtrack_f_DC_linear (Hz/s, early edge)",
        "Xtrack_f_DC_quadratic (Hz/s/s, early edge)",
        "Range_time_to_first_pixel (2way) (ms)",
        "Range_sampling_rate (computed, MHz)",
        "Total_range_band_width (MHz)",
        "Weighting_range",
    )

    keys_file = (
        "Datafile",
        "Dataformat",
        "Number_of_lines_original",
        "Number_of_pixels_original",
    )

    # --- 3. 打印详细参数数据块 ---
    print("\ncsk_dump_header2doris.py, doris software\n")
    print("**************************************************************")
    print("*_Start_readfiles:")
    print("**************************************************************")
    for key in keys_lead:
        print("{:<50}\t{}".format(key + ":", meta.get(key, "Unknown")))

    print("")
    print("**************************************************************")
    for key in keys_file:
        print("{:<50}\t{}".format(key + ":", meta.get(key, "Unknown")))
    print("**************************************************************")
    print("* End_readfiles:_NORMAL")
    print("**************************************************************")
    print("\n\n")
    
    # --- 4. 打印轨道数据块 ---
    print("**************************************************************")
    print("*_Start_leader_datapoints")
    print("**************************************************************")
    print(" t(s)		X(m)		Y(m)		Z(m)		VX(m/s)		VY(m/s)		VZ(m/s)")
    print("NUMBER_OF_DATAPOINTS: \t\t\t{}".format(meta["Orbit_n_pts"]))
    print("")

    # 输出轨道点
    for i in range(meta["Orbit_n_pts"]):
        print(
            "{:>12.3f} {:>15.3f} {:>15.3f} {:>15.3f} {:>12.3f} {:>12.3f} {:>12.3f}".format(
                hms2sec(meta["Orbit_Time"][i]),
                meta["Orbit_X"][i],
                meta["Orbit_Y"][i],
                meta["Orbit_Z"][i],
                meta["Orbit_VX"][i],
                meta["Orbit_VY"][i],
                meta["Orbit_VZ"][i],
            )
        )

    print("\n")
    print("**************************************************************")
    print("* End_leader_datapoints:_NORMAL")
    print("**************************************************************")

def lt4_dump_header2doris(source_meta_path, work_dir):
    """对齐 teresa 包的接口"""
    result_file = os.path.join(work_dir, "slave.res")
    meta = extract_lt4_meta(source_meta_path)
    
    with open(result_file, "w") as f:
        with redirect_stdout(f):
            write_res_file(meta)
            

# 独立测试入口
if __name__ == "__main__":
    source_meta_path = "/data/test/junjun/teresa_test_data/teresa_doris/lt4/first_priority/JZ1_MYC_STRIP1_013591_E113.3_N39.8_20260309_SLC_HH_L10000068320/JZ1_MYC_STRIP1_013591_E113.3_N39.8_20260309_SLC_HH_L10000068320.meta.xml"
    work_dir = "/data/test/junjun/teresa_test_data/teresa_doris/lt4/result"
    lt4_dump_header2doris(source_meta_path, work_dir)