import os
import h5py
from datetime import datetime
from contextlib import redirect_stdout

def extract_csk_meta(h5_file_path):
    """提取 CSK 参数并进行单位换算，以适配 Doris 格式"""
    meta = {}
    with h5py.File(h5_file_path, 'r') as f:
        # --- 基础文件信息 ---
        meta["Volume file"] = os.path.basename(h5_file_path)
        meta["Datafile"] = "image.raw"  # 对应 csk_dump_data 提取的二进制文件
        meta["Dataformat"] = "complex_short"

        # --- 对齐 BC 参数列表，填补缺失占位符 ---
        meta["Volume_ID"] = "CSK_Volume"
        meta["Volume_set_identifier"] = "CSK_Volume_Set"
        
        if 'S01/SBI' in f:
            shape = f['S01/SBI'].shape
            meta["Number_of_lines_original"] = shape[0]
            meta["Number_of_pixels_original"] = shape[1]
            meta["(Check)Number of records in ref. file"] = shape[0]
        else:
            meta["Number_of_lines_original"] = "Unknown"
            meta["Number_of_pixels_original"] = "Unknown"
            meta["(Check)Number of records in ref. file"] = "Unknown"

        meta["SAR_PROCESSOR"] = f.attrs.get('Processing Centre', b'Unknown').decode('utf-8')
        meta["Product type specifier"] = f.attrs.get('Product Type', b'Unknown').decode('utf-8')
        meta["Logical volume generating facility"] = "Unknown"
        meta["Logical volume creation date"] = "Unknown"
        meta["Location and date/time of product creation"] = "Unknown"
        
        # --- 场景与轨道识别 ---
        orbit_num = str(f.attrs.get('Orbit Number', 'Unknown'))
        direction = f.attrs.get('Orbit Direction', b'Unknown').decode('utf-8')
        mode = f.attrs.get('Acquisition Mode', b'Unknown').decode('utf-8')
        meta["Scene identification"] = f"Orbit: {orbit_num} {direction} Mode: {mode}"
        
        center_coords = f.attrs.get('Scene Centre Geodetic Coordinates', [0,0])
        lat = center_coords[0] if len(center_coords) > 0 else "Unknown"
        lon = center_coords[1] if len(center_coords) > 1 else "Unknown"
        meta["Scene_centre_latitude"] = lat
        meta["Scene_centre_longitude"] = lon
        meta["Scene location"] = f"lat: {lat} lon: {lon}"
        
        meta["Leader file"] = meta["Volume file"]
        meta["Sensor platform mission identifer"] = f.attrs.get('Satellite ID', b'Unknown').decode('utf-8')
        
        # --- 核心雷达与时间参数 ---
        meta["Radar_wavelength (m)"] = f.attrs['Radar Wavelength']
        
        start_utc_str = f.attrs['Scene Sensing Start UTC'].decode('utf-8')
        dt = datetime.strptime(start_utc_str[:26], '%Y-%m-%d %H:%M:%S.%f')
        meta["First_pixel_azimuth_time (UTC)"] = dt.strftime("%d-%b-%Y %H:%M:%S.%f").upper()
        
        # --- 内部高级雷达参数提取 (带宽、采样率等) ---
        if 'S01' in f:
            s01_attrs = f['S01'].attrs
            meta["Pulse_Repetition_Frequency (computed, Hz)"] = s01_attrs.get('PRF', "Unknown")
            sr = s01_attrs.get('Sampling Rate', "Unknown")
            meta["Range_sampling_rate (computed, MHz)"] = sr / 1e6 if sr != "Unknown" else "Unknown"
            
            az_bw = s01_attrs.get('Azimuth Focusing Bandwidth', "Unknown")
            rg_bw = s01_attrs.get('Range Focusing Bandwidth', "Unknown")
            meta["Total_azimuth_band_width (Hz)"] = az_bw
            meta["Total_range_band_width (MHz)"] = rg_bw / 1e6 if rg_bw != "Unknown" else "Unknown"
        else:
            meta["Pulse_Repetition_Frequency (computed, Hz)"] = "Unknown"
            meta["Range_sampling_rate (computed, MHz)"] = "Unknown"
            meta["Total_azimuth_band_width (Hz)"] = "Unknown"
            meta["Total_range_band_width (MHz)"] = "Unknown"
            
        if 'S01/B001' in f:
            range_first_time_sec = f['S01/B001'].attrs['Range First Times'][0]
            meta["Range_time_to_first_pixel (2way) (ms)"] = range_first_time_sec * 1000.0
        else:
            meta["Range_time_to_first_pixel (2way) (ms)"] = "Unknown"

        meta["Weighting_azimuth"] = "Unknown"
        meta["Weighting_range"] = "Unknown"

        dc_poly = f.attrs.get('Centroid vs Azimuth Time Polynomial', [0.0])
        meta["Xtrack_f_DC_constant (Hz, early edge)"] = dc_poly[0] if len(dc_poly) > 0 else 0.0
        meta["Xtrack_f_DC_linear (Hz/s, early edge)"] = 0.0
        meta["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"] = 0.0

        meta["State_Vectors_Times"] = f.attrs['State Vectors Times'].tolist()
        meta["ECEF_Satellite_Position"] = f.attrs['ECEF Satellite Position'].tolist()
        meta["Orbit_n_pts"] = len(meta["State_Vectors_Times"])

    return meta

def write_res_file(meta):
    """将字典输出为 Doris 识别的文本格式"""
    
    # --- 1. 打印 Doris 必须的起始信息和流程控制记分牌 ---
    print("===========================================================")
    print("           TERESA - 国产卫星 SAR 图像配准工具 (CSK)")
    print("===========================================================")
    print("File Generated  : ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("File Type       : SAR Registration Metadata")
    print("Input Mission   : CSK")
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
    print(" t(s)		X(m)		Y(m)		Z(m)")
    print("NUMBER_OF_DATAPOINTS: \t\t\t{}".format(meta["Orbit_n_pts"]))
    print("")

    # 输出轨道点
    for i in range(meta["Orbit_n_pts"]):
        t = meta["State_Vectors_Times"][i]
        x, y, z = meta["ECEF_Satellite_Position"][i]
        print(" {:>7.3f} {:>15.3f} {:>15.3f} {:>15.3f}".format(t, x, y, z))

    print("\n")
    print("**************************************************************")
    print("* End_leader_datapoints:_NORMAL")
    print("**************************************************************")

def csk_dump_header2doris(source_meta_path, work_dir):
    """对齐 teresa 包的接口"""
    result_file = os.path.join(work_dir, "slave.res")
    meta = extract_csk_meta(source_meta_path)
    
    with open(result_file, "w") as f:
        with redirect_stdout(f):
            write_res_file(meta)
            
    print(f"CSK 头文件已成功生成: {result_file}")

# 独立测试入口
if __name__ == "__main__":
    pass