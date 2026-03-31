#!/home/yuxiao/.virtualenvs/doris/bin/python3

# import os
# activate_venv_path = os.path.join('/home/yuxiao/.virtualenvs/doris/', 'bin/activate_this.py')
# with open(activate_venv_path) as f:
#     exec(f.read(), {'__file__': activate_venv_path})

import os
from contextlib import redirect_stdout
import fnmatch
from typing import Any, Dict
from xml.etree import ElementTree
from datetime import datetime, timedelta


SPEED_OF_LIGHT = 299792458


def strftime_doris(dt):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{dt.day:02d}-{months[dt.month - 1]}-{dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.{dt.microsecond:06d}"



def locate(pattern: str, root=os.curdir) -> str:
    # region docstring
    """Locate the **first** file matching supplied filename pattern
    in and below supplied root directory.

    Parameters
    ----------
    pattern : str
        The pattern that you're looking for. The pattern follows the same rule
        as in linux system, as "*" is allowed.
    root : str, optional
        the root directory for searching the pattern, by default os.curdir.

    Returns
    -------
    str
        the path to the **first** matched file.

    Notes
    -----
    You can use either "return" or "yield", but be aware of the diference
    between the two.
    """
    # endregion

    # TODO: consider using os.getcwd()?
    # see https://stackmirror.com/questions/14512087
    for path, dirs, files in os.walk(os.path.abspath(root), followlinks=True):
        for filename in fnmatch.filter(files, pattern):
            return os.path.join(path, filename)
    raise FileNotFoundError


def hms2sec(hmsString, convertFlag="int"):
    # convert HMS 2 sec for orbit files.
    # input hmsString syntax: XX:XX:XX.xxxxxx
    secString = (
        int(hmsString[11:13]) * 3600
        + int(hmsString[14:16]) * 60
        + float(hmsString[17:])
    )
    if convertFlag == "int":
        return round(secString)
    elif convertFlag == "float":
        return float(secString)
    else:
        return round(secString)

def reverse_time(cur_time: datetime):
    current_day = cur_time.replace(microsecond=0, second=0, minute=0, hour=0)
    next_day = current_day + timedelta(days=1)
    time2nextday = next_day - cur_time
    reversed_time = current_day + time2nextday
    return reversed_time


class BC:
    """Implementing the S-1 Format for FC1 reader.

    author: Yuxiao QIN
    date: 2024-July
    """

    def __init__(self):
        """[summary]"""
        self.meta = {}  # meta file, empty dictionary

    def locate_meta(self, directory: str):
        """locate the XML file in the directory.

        Parameters
        ----------
        directory : str
            [description]
        """
        pattern = "bc3-sm-slc*.xml"
        self.meta["path"] = locate(pattern, directory)

        return self
    def read_meta(self) -> None:
        """Read and parse metadata from XML file."""
        query_list: dict = {
            # volume info
            "Volume file": self.meta["path"],
            "Volume_ID": "adsHeader/missionId",
            "Volume_identifier": "adsHeader/missionId",
            "Volume_set_identifier": "adsHeader/missionId",
            # mission info
            "(Check)Number of records in ref. file": "imageAnnotation/imageInformation/numberOfLines",
            "SAR_PROCESSOR": None,
            "Product type specifier": "adsHeader/productType",
            "Logical volume generating facility": None,
            "Logical volume creation date": None,
            "Location and date/time of product creation": None,
            "Orbit": "adsHeader/absoluteOrbitNumber",
            "Heading_platform": "generalAnnotation/productInformation/platformHeading",
            "Direction": "generalAnnotation/productInformation/pass",
            "Mode": "adsHeader/mode",
            "Leader file": self.meta["path"],
            "Sensor platform mission identifer": "adsHeader/missionId",
            "Scene_centre_latitude": None,
            "Scene_centre_longitude": None,
            "Scene_corner_latitude": None,
            "Scene_corner_longitude": None,
            "Reference_range": "imageAnnotation/processingInformation/referenceRange",
            "Ellipsoid_semi_major_axis": "imageAnnotation/processingInformation/ellipsoidSemiMajorAxis",
            "Ellipsoid_semi_minor_axis": "imageAnnotation/processingInformation/ellipsoidSemiMinorAxis",
            # product info
            "Radar_wavelength (m)": "generalAnnotation/productInformation/radarFrequency",
            "First_pixel_azimuth_time (UTC)": "imageAnnotation/imageInformation/productFirstLineUtcTime",
            "Last_pixel_azimuth_time (UTC)": "imageAnnotation/imageInformation/productLastLineUtcTime",
            "Pulse_Repetition_Frequency (computed, Hz)": "generalAnnotation/downlinkInformationList/downlinkInformation/prf",
            "Total_azimuth_band_width (Hz)": "imageAnnotation/processingInformation/swathProcParamsList/swathProcParams/azimuthProcessing/totalBandwidth",
            "Azimuth_proc_bandwidth": "imageAnnotation/processingInformation/swathProcParamsList/swathProcParams/azimuthProcessing/processingBandwidth",
            "Incidence_angle_mid_swath": "imageAnnotation/imageInformation/incidenceAngleMidSwath",
            "Weighting_azimuth": None,
            "Doppler_Coef": "dopplerCentroid/dcEstimateList/dcEstimate/dataDcPolynomial",
            "Xtrack_f_DC_constant (Hz, early edge)": None,
            "Xtrack_f_DC_linear (Hz/s, early edge)": None,
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)": None,
            "Range_time_to_first_pixel (2way) (ms)": "imageAnnotation/imageInformation/slantRangeTime",
            "Range_sampling_rate (computed, MHz)": "generalAnnotation/productInformation/rangeSamplingRate",
            "Total_range_band_width (MHz)": "imageAnnotation/processingInformation/swathProcParamsList/swathProcParams/rangeProcessing/totalBandwidth",
            "Weighting_range": None,
            "Antenna_side": "imageAnnotation/imageInformation/look_side",
            # SLC info
            "Datafile": None,
            "Dataformat": "adsHeader/productType",
            "Number_of_lines_original": "imageAnnotation/imageInformation/numberOfLines",
            "Number_of_pixels_original": "imageAnnotation/imageInformation/numberOfSamples",
            "Range_pixel_spacing": "imageAnnotation/imageInformation/rangePixelSpacing",
            "Azimuth_pixel_spacing": "imageAnnotation/imageInformation/azimuthPixelSpacing",
            # Orbit
            "Orbit Time": "generalAnnotation/orbitList/orbit/time",
            "Orbit X": "generalAnnotation/orbitList/orbit/position/x",
            "Orbit Y": "generalAnnotation/orbitList/orbit/position/y",
            "Orbit Z": "generalAnnotation/orbitList/orbit/position/z",
            "Orbit VX": "generalAnnotation/orbitList/orbit/velocity/x",
            "Orbit VY": "generalAnnotation/orbitList/orbit/velocity/y",
            "Orbit VZ": "generalAnnotation/orbitList/orbit/velocity/z",
            # Geolocation
            "latitude": "geolocationGrid/geolocationGridPointList/geolocationGridPoint/latitude",
            "longitude": "geolocationGrid/geolocationGridPointList/geolocationGridPoint/longitude",
            "terrain_height": "generalAnnotation/terrainHeightList/terrainHeight/value"
        }

        # Initialize container
        container: Dict[str, Any] = {
            "Orbit Time": [],
            "Orbit X": [],
            "Orbit Y": [],
            "Orbit Z": [],
            "Orbit VX": [],
            "Orbit VY": [],
            "Orbit VZ": [],
            "latitude": [],
            "longitude": [],
        }

        # Parse XML
        root = ElementTree.parse(self.meta["path"]).getroot()

        for key, xpath in query_list.items():
            if xpath is None:
                container[key] = "Unknown"
            elif xpath == self.meta["path"]:  # file paths
                container[key] = str(self.meta["path"])
            elif key in ["Orbit Time", "Orbit X", "Orbit Y", "Orbit Z", "Orbit VX", "Orbit VY", "Orbit VZ", "latitude", "longitude"]:
                # Handle list elements
                elements = root.findall(xpath)
                for elem in elements:
                    if elem is not None and elem.text is not None:
                        container[key].append(elem.text)
            else:
                # Handle single elements
                elem = root.find(xpath)
                container[key] = elem.text if elem is not None and elem.text is not None else "Unknown"

        # Calculate additional metadata
        container["Orbit_n_pts"] = len(container["Orbit Time"])

        # # Scene center coordinates
        # geolocation_list = root.find('geolocationGrid/geolocationGridPointList')
        # count = int(geolocation_list.get('count')) if geolocation_list is not None else len(container["latitude"])
        # center_scene_index = (count - 1) // 2
        # container["Scene_centre_latitude"] = float(container["latitude"][center_scene_index])
        # container["Scene_centre_longitude"] = float(container["longitude"][center_scene_index])

        # === 修正：从 geolocationGrid 提取四角点和中心坐标 ===
        geolocation_points = root.findall('geolocationGrid/geolocationGridPointList/geolocationGridPoint')
        if len(geolocation_points) == 4:
            # 顺序：左上(0,0)、右上(0,w-1)、左下(h-1,0)、右下(h-1,w-1)
            lat_vals = [float(p.find('latitude').text) for p in geolocation_points]
            lon_vals = [float(p.find('longitude').text) for p in geolocation_points]

            # 保存四角点
            container["Scene_corner_latitude"] = lat_vals  # [lat1, lat2, lat3, lat4]
            container["Scene_corner_longitude"] = lon_vals  # [lon1, lon2, lon3, lon4]

            # 计算中心点（取四个角的平均）
            container["Scene_centre_latitude"] = sum(lat_vals) / 4.0
            container["Scene_centre_longitude"] = sum(lon_vals) / 4.0
        else:
            # If it's not scene centre coordinate system
            geolocation_list = root.find('geolocationGrid/geolocationGridPointList')
            count = int(geolocation_list.get('count')) if geolocation_list is not None else len(container["latitude"])
            center_scene_index = (count - 1) // 2
            container["Scene_centre_latitude"] = float(container["latitude"][center_scene_index])
            container["Scene_centre_longitude"] = float(container["longitude"][center_scene_index])
            container["Scene_corner_latitude"] = [container["Scene_centre_latitude"]] * 4
            container["Scene_corner_longitude"] = [container["Scene_centre_longitude"]] * 4

        container["Scene identification"] = (
            f"Orbit: {container['Orbit']} {container['Direction']} Mode: {container['Mode']}"
        )
        container["Scene location"] = (
            f"lat: {container['Scene_centre_latitude']} lon: {container['Scene_centre_longitude']}"
        )
        # Data file
        container["Datafile"] = os.path.basename(
            locate("bc*slc*.tiff", os.path.dirname(self.meta["path"]))
        )

        # Convert units and formats
        # Range time to ms
        container["Range_time_to_first_pixel (2way) (ms)"] = (
            1000 * float(container["Range_time_to_first_pixel (2way) (ms)"])
        )

        # Range sampling rate and bandwidth to MHz
        container["Range_sampling_rate (computed, MHz)"] = (
            float(container["Range_sampling_rate (computed, MHz)"]) / 1e6
        )
        container["Total_range_band_width (MHz)"] = (
            float(container["Total_range_band_width (MHz)"]) / 1e6
        )

        # Wavelength calculation
        container["Radar_wavelength (m)"] = (
            SPEED_OF_LIGHT / float(container["Radar_wavelength (m)"])
        )

        # Doppler coefficients
        # --- 新增：根据天线方向和轨道方向决定多普勒符号处理 ---
        # 左视卫星需要反转多普勒符号（物理规则）
        doppler_sign = -1 if container["Antenna_side"] == "LEFT" else 1
        doppler_coeffs = container["Doppler_Coef"].split()
        container["Xtrack_f_DC_constant (Hz, early edge)"] = doppler_coeffs[0] if len(doppler_coeffs) > 0 else "0.0"
        container["Xtrack_f_DC_linear (Hz/s, early edge)"] = doppler_coeffs[1] if len(doppler_coeffs) > 1 else "0.0"
        container["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"] = doppler_coeffs[2] if len(doppler_coeffs) > 2 else "0.0"
        # 应用符号调整（注意：升轨已做时间反转，这里只需统一处理符号）
        container["Xtrack_f_DC_constant (Hz, early edge)"] = str(
            doppler_sign * float(container["Xtrack_f_DC_constant (Hz, early edge)"]))
        container["Xtrack_f_DC_linear (Hz/s, early edge)"] = str(doppler_sign *
                                                                 float(container["Xtrack_f_DC_linear (Hz/s, early edge)"]))
        container["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"] = str(doppler_sign *
                                                                      float(container["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"]))
        # Time handling for ascending orbits
        cur_time_start = datetime.strptime(container["First_pixel_azimuth_time (UTC)"], "%Y-%m-%dT%H:%M:%S.%f")
        cur_time_end = datetime.strptime(container["Last_pixel_azimuth_time (UTC)"], "%Y-%m-%dT%H:%M:%S.%f")
        # if container["Antenna_side"] == "LEFT":
        #     cur_time_start = datetime.strptime(container["Last_pixel_azimuth_time (UTC)"], "%Y-%m-%dT%H:%M:%S.%f")
        #     cur_time_end = datetime.strptime(container["First_pixel_azimuth_time (UTC)"], "%Y-%m-%dT%H:%M:%S.%f")
        #     cur_time_start = reverse_time(cur_time_start)
        #     cur_time_end = reverse_time(cur_time_end)

        # datetime.strftime(cur_time_start, DORIS_DATETIME_FORMAT)
        # datetime.strftime(cur_time_end, DORIS_DATETIME_FORMAT)
        container["First_pixel_azimuth_time (UTC)"] = strftime_doris(cur_time_start)
        container["Last_pixel_azimuth_time (UTC)"] = strftime_doris(cur_time_end)

        # Fixed values
        container["SAR_PROCESSOR"] = "HL"
        container["Logical volume generating facility"] = "HL"
        container["Product type specifier"] = "BC3"
        container["Sensor platform mission identifer"] = "BC3"

        container["Terrain_height"] = float(container.get("terrain_height", 0.0))
        self.meta.update(container)

    def export2res(self) -> None:
        """Export metadata to Doris .res format."""

        # Header keys (same as original)
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
            "Heading_platform",
            "Leader file",
            "Sensor platform mission identifer",
            "Scene_centre_latitude",
            "Scene_centre_longitude",
            "Scene_corner_latitude",
            "Scene_corner_longitude",
            "Reference_range",
            "Ellipsoid_semi_major_axis",
            "Ellipsoid_semi_minor_axis",
            "Radar_wavelength (m)",
            "First_pixel_azimuth_time (UTC)",
            "Last_pixel_azimuth_time (UTC)",
            "Pulse_Repetition_Frequency (computed, Hz)",
            "Total_azimuth_band_width (Hz)",
            "Azimuth_proc_bandwidth",
            "Weighting_azimuth",
            "Incidence_angle_mid_swath",
            "Xtrack_f_DC_constant (Hz, early edge)",
            "Xtrack_f_DC_linear (Hz/s, early edge)",
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)",
            "Range_time_to_first_pixel (2way) (ms)",
            "Range_sampling_rate (computed, MHz)",
            "Total_range_band_width (MHz)",
            "Weighting_range",
            "Antenna_side",
            "Terrain_height"
        )

        keys_file = (
            "Datafile",
            "Dataformat",
            "Number_of_lines_original",
            "Number_of_pixels_original",
            "Range_pixel_spacing",
            "Azimuth_pixel_spacing"
        )

        # Print header
        print("**************************************************************")
        print("*Processing_Status_Flag:")
        print("**************************************************************")
        print("Start_process_control")
        print("readfiles:\t\t1")
        print("precise_orbits:\t\t0")
        print("modify_orbits:\t\t0")
        print("crop:\t\t1")
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
        print("\nBCHeaderReader v1.0, doris software, 2024\n")
        print("**************************************************************")
        print("*_Start_readfiles:")
        print("**************************************************************")

        # Print lead keys
        for key in keys_lead:
            print("{:<50}\t{}".format(key + ":", self.meta[key]))

        print("")
        print("**************************************************************")

        # Print file keys
        for key in keys_file:
            print("{:<50}\t{}".format(key + ":", self.meta[key]))

        print("**************************************************************")
        print("* End_readfiles:_NORMAL")
        print("**************************************************************")
        print("")
        print("")
        print("**************************************************************")
        print("*_Start_leader_datapoints")
        print("**************************************************************")
        print(" t(s)\t\tX(m)\t\tY(m)\t\tZ(m)\t\tVX(m/s)\t\tVY(m/s)\t\tVZ(m\s)")
        # print(" t(s)\t\tX(m)\t\tY(m)\t\tZ(m)")
        print("NUMBER_OF_DATAPOINTS: \t\t\t{}".format(self.meta["Orbit_n_pts"]))
        print("")

        # Print orbit data (with reversal for ascending orbits)
        # if self.meta["Direction"] == "ASCENDING":
        #     for i in reversed(range(self.meta["Orbit_n_pts"])):
        #         x, y, z = self.meta["Orbit X"][i], self.meta["Orbit Y"][i], self.meta["Orbit Z"][i]
        #         vx, vy, vz = self.meta["Orbit VX"][i], self.meta["Orbit VY"][i], self.meta["Orbit VZ"][i]
        #         cur_orb_time = self.meta["Orbit Time"][i]
        #         cur_orb_time_dt = datetime.strptime(cur_orb_time, "%Y-%m-%dT%H:%M:%S.%f")
        #         cur_orb_time_dt = reverse_time(cur_orb_time_dt)
        #         cur_orb_time_str = datetime.strftime(cur_orb_time_dt, "%Y-%m-%dT%H:%M:%S.%f")
        #         # print(" {:>7} {:>15} {:>15} {:>15}".format(
        #         #     hms2sec(cur_orb_time_str, convertFlag="float"), x, y, z
        #         # ))
        #         print(" {:>7} {:>15} {:>15} {:>15} {:>15} {:>15} {:>15}".format(
        #             hms2sec(cur_orb_time_str, convertFlag="float"), x, y, z, vx, vy, vz
        #         ))
        # else:
        for i in range(self.meta["Orbit_n_pts"]):
            x, y, z = self.meta["Orbit X"][i], self.meta["Orbit Y"][i], self.meta["Orbit Z"][i]
            vx, vy, vz = self.meta["Orbit VX"][i], self.meta["Orbit VY"][i], self.meta["Orbit VZ"][i]
            cur_orb_time = self.meta["Orbit Time"][i]
            # print(" {:>7} {:>15} {:>15} {:>15}".format(
            #     hms2sec(cur_orb_time, convertFlag="float"), x, y, z
            # ))
            print(" {:>7} {:>15} {:>15} {:>15} {:>15} {:>15} {:>15}".format(
                hms2sec(cur_orb_time, convertFlag="float"), x, y, z, vx, vy, vz
            ))

        print("\n")
        print("**************************************************************")
        print("* End_leader_datapoints:_NORMAL")
        print("**************************************************************")

    def usage(self):
        print("===========================================================")
        print("           TERESA - 国产卫星 SAR 图像配准工具")
        print("===========================================================")
        print("Software Name   : TERESA (Tool for Enhanced Registration of Earth SAR imagery Automatically)")
        print("Version         : v0.1.0")
        print("Release Date    : 2025-07-31")
        print("")
        print("Developed by    : APRILab (Automated Phase Reconstruction and Interferometry Lab)")
        print("Affiliation     : 西北工业大学 电子信息学院")
        print("Website         : https://github.com/aprilab-dev")
        print("Contact Email   : yuxiao.qin@nwpu.edu.cn")
        print("")
        print("File Generated  : ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("File Type       : SAR Registration Metadata")
        print("Input Mission   : fc1")
        print("")
        print("Description     : 本文件标记了配准处理过程，SAR 图像的基本信息等。")
        print("")
        print("-----------------------------------------------------------")
        print("")
        print("**************************************************************")
        print("*Processing_Status_Flag:")
        print("**************************************************************")
        print("Start_process_control")
        print("readfiles:\t\t1")
        print("precise_orbits:\t\t0")
        print("modify_orbits:\t\t0")
        print("crop:\t\t1")
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

def bc_dump_header2doris(source_meta_path, work_dir):

    result_file = os.path.join(work_dir, "slave.res")
    bc = BC()

    bc.meta["path"] = source_meta_path
    with open(result_file, "w") as f:
        with redirect_stdout(f):
            bc.usage()
            bc.read_meta()
            bc.export2res()