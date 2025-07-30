#!/usr/bin/env python3

import glob
import os
# activate_venv_path = os.path.join('/home/junjun/.local/doris/doris/', 'bin/activate_this.py')
# with open(activate_venv_path) as f:
#     exec(f.read(), {'__file__': activate_venv_path})
# 我的修改，注释掉了两句打印
# print(f"ERROR   : No orbit files found matching pattern {orbit_pattern} in {orbit_dir}")
# print(f"INFO    : Looking for orbit files between {start_date_str} and {end_date_str} (Beijing Time)...")

import os
from contextlib import redirect_stdout
import fnmatch
from typing import Any, Dict
from xml.etree import ElementTree
from datetime import datetime, timedelta


SPEED_OF_LIGHT = 299792458
TIME_OFFSET = 8  # time offset between UTC and external orbit file


def locate(pattern: str, root=os.curdir) -> str:
    """Locate the first file matching pattern in directory tree"""
    for path, dirs, files in os.walk(os.path.abspath(root), followlinks=True):
        for filename in fnmatch.filter(files, pattern):
            return os.path.join(path, filename)
    raise FileNotFoundError


def hms2sec(timestr: str, convertFlag: str = "int") -> float:
    """Convert time string to seconds"""
    time_parts = timestr.split('T')[1].split(':')
    secString = (
        int(time_parts[0]) * 3600
        + int(time_parts[1]) * 60
        + float(time_parts[2])
    )
    if convertFlag == "int":
        return round(secString)
    elif convertFlag == "float":
        return float(secString)
    else:
        return round(secString)


class LT1:
    """LT1 is used to read LuTan-1 (LT1) meta data and to make it compatible
    with the DORIS (v4) input.

    author: Yuxiao QIN
    date: 2025-Jan
    """

    def __init__(self):
        """Initialize empty metadata dictionary"""
        self.meta = {}

    def locate_meta(self, directory: str):
        """Locate metadata file in directory"""
        pattern = "LT1*SLC*.meta.xml"
        self.meta["path"] = locate(pattern, directory)
        return self

    def read_meta(self):
        """Read and format metadata from XML file"""
        query_list = {
            # volume info
            "Volume file"                                 : self.meta["path"],
            "Volume_ID"                                   : "generalHeader//itemName",
            "Volume_identifier"                           : "productInfo//generationInfo//logicalProductID",
            "Volume_set_identifier"                       : None,
            # mission info
            "(Check)Number of records in ref. file"       : "productInfo//imageDataInfo//imageRaster//numberOfRows",
            "SAR_PROCESSOR"                               : "generalHeader//generationSystem",
            "Product type specifier"                      : "generalHeader//mission",
            "Logical volume generating facility"          : "productInfo//generationInfo//level1ProcessingFacility",
            "Logical volume creation date"                : "generalHeader//generationTime",
            "Location and date/time of product creation"  : "generalHeader//generationTime",
            "Orbit"                                       : "productInfo//missionInfo//absOrbit",
            "Direction": "productInfo//missionInfo//orbitDirection",
            "Mode": "productInfo//acquisitionInfo//imagingMode",
            "Leader file": self.meta["path"],
            "Sensor platform mission identifer": "generalHeader//mission",
            "Scene_centre_latitude": "productInfo//sceneInfo//sceneCenterCoord//lat",
            "Scene_centre_longitude": "productInfo//sceneInfo//sceneCenterCoord//lon",
            # product info
            "Radar_wavelength (m)": None,  # Will calculate from centerFrequency
            "First_pixel_azimuth_time (UTC)": "productInfo//sceneInfo//start//timeUTC",
            "Last_pixel_azimuth_time (UTC)": "productInfo//sceneInfo//stop//timeUTC",
            "Pulse_Repetition_Frequency (computed, Hz)": "instrument//settings//settingRecord//PRF",
            "Total_azimuth_band_width (Hz)": "processing//processingParameter//totalProcessedAzimuthBandwidth",
            "Weighting_azimuth": "processing//processingParameter//azimuthWindowID",
            "Xtrack_f_DC_constant (Hz, early edge)": None,
            "Xtrack_f_DC_linear (Hz/s, early edge)": None,
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)": None,
            "Range_time_to_first_pixel (2way) (ms)": "productInfo//sceneInfo//rangeTime//firstPixel",
            "Range_sampling_rate (computed, MHz)": "instrument//settings//RSF",
            "Total_range_band_width (MHz)": "processing//processingParameter//totalProcessedRangeBandwidth",
            "Weighting_range": "processing//processingParameter//rangeWindowID",
            # SLC info
            "Datafile": None,
            "Dataformat": "productInfo//imageDataInfo//imageDataFormat",
            "Number_of_lines_original": "productInfo//imageDataInfo//imageRaster//numberOfRows",
            "Number_of_pixels_original": "productInfo//imageDataInfo//imageRaster//numberOfColumns",
            # Orbit data
            "Orbit Time": "platform//orbit//stateVec//timeUTC",
            "Orbit X": "platform//orbit//stateVec//posX",
            "Orbit Y": "platform//orbit//stateVec//posY",
            "Orbit Z": "platform//orbit//stateVec//posZ",
        }

        # Initialize containers for orbit data
        container: Dict[str, Any] = {
            "Orbit Time": [],
            "Orbit X": [],
            "Orbit Y": [],
            "Orbit Z": [],
        }

        # Parse XML
        root = ElementTree.parse(self.meta["path"]).getroot()

        # Get values from XML
        for key, value in query_list.items():
            if value is None:
                container[key] = "Unknown"
            elif value.endswith(".xml"):
                container[key] = os.path.basename(value)
            else:
                for item in root.findall(value):
                    if key.startswith("Orbit "):
                        container[key].append(item.text)
                    else:
                        container[key] = item.text

        # Calculate radar wavelength
        center_freq = float(root.find("instrument//radarParameters//centerFrequency").text)
        container["Radar_wavelength (m)"] = str(SPEED_OF_LIGHT / center_freq)

        # Convert bandwidth values from Hz to MHz
        for key in ["Range_sampling_rate (computed, MHz)", "Total_range_band_width (MHz)"]:
            if key in container and container[key] is not None:
                try:
                    value_hz = float(container[key])
                    container[key] = str(value_hz / 1e6)
                except (ValueError, TypeError):
                    print(f"Warning: Could not convert {key} to MHz")
                    container[key] = "Unknown"

        # Get Doppler coefficients
        doppler_coeffs = root.findall("processing//doppler//dopplerCentroid//dopplerEstimate//combinedDoppler//coefficient")
        if doppler_coeffs:
            container["Xtrack_f_DC_constant (Hz, early edge)"] = doppler_coeffs[0].text
            container["Xtrack_f_DC_linear (Hz/s, early edge)"] = doppler_coeffs[1].text if len(doppler_coeffs) > 1 else "0"
            container["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"] = doppler_coeffs[2].text if len(doppler_coeffs) > 2 else "0"

        # Manual updates
        container["Orbit_n_pts"] = len(container["Orbit Time"])
        container["Volume_set_identifier"] = "DUMMY"
        container["Scene identification"] = (
            f"Orbit: {container['Orbit']} {container['Direction']} Mode: {container['Mode']}"
        )
        container["Scene location"] = (
            f"lat: {container['Scene_centre_latitude']} lon: {container['Scene_centre_longitude']}"
        )
        container["Datafile"] = os.path.basename(
            locate("LT1*SLC*.tiff", os.path.dirname(self.meta["path"]))
        )

        # Convert range time to ms
        container["Range_time_to_first_pixel (2way) (ms)"] = str(float(container["Range_time_to_first_pixel (2way) (ms)"]) * 1000)

        # Update time format
        container["First_pixel_azimuth_time (UTC)"] = (
            datetime.strptime(
                container["First_pixel_azimuth_time (UTC)"],
                "%Y-%m-%dT%H:%M:%S.%f"
            ).strftime("%d-%b-%Y %H:%M:%S.%f")
        )
        container["Last_pixel_azimuth_time (UTC)"] = (
            datetime.strptime(
                container["Last_pixel_azimuth_time (UTC)"],
                "%Y-%m-%dT%H:%M:%S.%f"
            ).strftime("%d-%b-%Y %H:%M:%S.%f")
        )

        self.meta.update(container)
        return self

    def export2res(self) -> None:
        """Export metadata in DORIS-compatible format"""
        keys_lead = (
            "Volume file", "Volume_ID", "Volume_set_identifier",
            "(Check)Number of records in ref. file", "SAR_PROCESSOR",
            "Product type specifier", "Logical volume generating facility",
            "Logical volume creation date", "Location and date/time of product creation",
            "Scene identification", "Scene location", "Leader file",
            "Sensor platform mission identifer", "Scene_centre_latitude",
            "Scene_centre_longitude", "Radar_wavelength (m)",
            "First_pixel_azimuth_time (UTC)", "Pulse_Repetition_Frequency (computed, Hz)",
            "Total_azimuth_band_width (Hz)", "Weighting_azimuth",
            "Xtrack_f_DC_constant (Hz, early edge)", "Xtrack_f_DC_linear (Hz/s, early edge)",
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)",
            "Range_time_to_first_pixel (2way) (ms)", "Range_sampling_rate (computed, MHz)",
            "Total_range_band_width (MHz)", "Weighting_range"
        )

        keys_file = (
            "Datafile", "Dataformat", "Number_of_lines_original",
            "Number_of_pixels_original"
        )

        print("\nlt1_dump_header2doris.py v1.0, doris software, 2024\n")
        print("**************************************************************")
        print("*_Start_readfiles:")
        print("**************************************************************")

        for keys in keys_lead:
            print("{:<50}\t{}".format(keys + ":", self.meta[keys]))

        print("\n**************************************************************")
        for keys in keys_file:
            print("{:<50}\t{}".format(keys + ":", self.meta[keys]))

        print("**************************************************************")
        print("* End_readfiles:_NORMAL")
        print("**************************************************************\n\n")
        print("**************************************************************")
        print("*_Start_leader_datapoints")
        print("**************************************************************")
        print(" t(s)		X(m)		Y(m)		Z(m)")
        print(f"NUMBER_OF_DATAPOINTS: 			{self.meta['Orbit_n_pts']}\n")

        for i in range(self.meta["Orbit_n_pts"]):
            x, y, z = [self.meta[f"Orbit {coord}"][i] for coord in "XYZ"]
            print(f" {hms2sec(self.meta['Orbit Time'][i]):>7} {x:>15} {y:>15} {z:>15}")

        print("\n**************************************************************")
        print("* End_leader_datapoints:_NORMAL")
        print("**************************************************************")

    def _locate_external_orbit(self):
        """Locate external orbit file"""
        # Get start/end time from meta and convert to Beijing time (UTC+8)

        start_time_utc = datetime.strptime(self.meta["First_pixel_azimuth_time (UTC)"], "%d-%b-%Y %H:%M:%S.%f")
        end_time_utc = datetime.strptime(self.meta["Last_pixel_azimuth_time (UTC)"], "%d-%b-%Y %H:%M:%S.%f")

        beijing_offset = TIME_OFFSET # UTC+8
        start_time_beijing = start_time_utc + timedelta(hours=beijing_offset)
        end_time_beijing = end_time_utc + timedelta(hours=beijing_offset)

        # Format times for orbit file search
        start_date_str = start_time_beijing.strftime("%Y%m%d")
        end_date_str = end_time_beijing.strftime("%Y%m%d")

        # print(f"INFO    : Looking for orbit files between {start_date_str} and {end_date_str} (Beijing Time)...")

        # Get product type (A or B) from meta
        product_type = self.meta["Product type specifier"][-1]  # Get last character (A or B)

        # Check for orbit file in ../../orbits directory
        orbit_dir = os.path.join(os.path.dirname(self.meta["path"]), "../../orbits")
        orbit_pattern = f"LT1{product_type}_GpsData_*_{start_date_str}.txt"
        orbit_path = os.path.join(orbit_dir, orbit_pattern)

        # Use glob to find matching files
        matching_files = glob.glob(orbit_path)

        if not matching_files:
            # print(f"ERROR   : No orbit files found matching pattern {orbit_pattern} in {orbit_dir}")
            return None

        # print(f"INFO    : Found orbit file(s): {', '.join(matching_files)}")
        return matching_files[0]

    def _read_external_orbit(self, orbit_path: str):
        """Read external orbit data

        Args:
            orbit_path: Path to the orbit file

        This function reads orbit data from the specified file, filtering for data points
        between start_time_utc-60s and end_time_utc+60s. Only FIXED coordinates are used.
        """

        # Initialize container for orbit data
        container = {
            "Orbit Time": [],
            "Orbit X": [],
            "Orbit Y": [],
            "Orbit Z": [],
        }

        # Get start and end times with buffer
        start_time_utc = datetime.strptime(self.meta["First_pixel_azimuth_time (UTC)"], "%d-%b-%Y %H:%M:%S.%f")
        end_time_utc = datetime.strptime(self.meta["Last_pixel_azimuth_time (UTC)"], "%d-%b-%Y %H:%M:%S.%f")


        beijing_offset = TIME_OFFSET # UTC+8
        start_time_beijing = start_time_utc + timedelta(hours=beijing_offset)
        end_time_beijing = end_time_utc + timedelta(hours=beijing_offset)

        start_time_buffer = start_time_beijing - timedelta(seconds=120)
        end_time_buffer = end_time_beijing + timedelta(seconds=120)

        print(f"INFO    : Reading orbits from {start_time_buffer} to {end_time_buffer}")

        with open(orbit_path, 'r') as file:
            # Skip header lines (first 5 lines)
            for _ in range(5):
                next(file)

            # Read and process each data line
            for line in file:
                if not line.strip() or line.startswith('#'):
                    continue

                parts = line.split()

                # Parse time components
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                hour = int(parts[3])
                minute = int(parts[4])
                second = float(parts[5])

                # Create datetime object for comparison
                current_time = datetime(year, month, day, hour, minute) + timedelta(seconds=second)

                # Check if within time window
                if start_time_buffer <= current_time <= end_time_buffer:
                    # Convert from Beijing time (UTC+8) to UTC by subtracting 8 hours
                    utc_time = current_time - timedelta(hours=TIME_OFFSET)
                    # Format time string in the required format
                    time_str = utc_time.strftime("%Y-%m-%dT%H:%M:%S.%f")

                    # Extract FIXED coordinates
                    x = parts[6]  # FIXED-PX
                    y = parts[7]  # FIXED-PY
                    z = parts[8]  # FIXED-PZ

                    # Store in container
                    container["Orbit Time"].append(time_str)
                    container["Orbit X"].append(x)
                    container["Orbit Y"].append(y)
                    container["Orbit Z"].append(z)

        # Update the meta dictionary with the new orbit data
        self.meta.update(container)
        self.meta["Orbit_n_pts"] = len(container["Orbit Time"])

        print(f"INFO    : Read {self.meta['Orbit_n_pts']} orbit points")
        return self

    def update_external_orbit(self):

        # Check for external orbit file
        f_orbit = self._locate_external_orbit()
        if f_orbit is None:
            return self

        # Save internal orbit data with modified keys
        self.meta["Orbit Time(internal)"] = self.meta.pop("Orbit Time")
        self.meta["Orbit X(internal)"] = self.meta.pop("Orbit X")
        self.meta["Orbit Y(internal)"] = self.meta.pop("Orbit Y")
        self.meta["Orbit Z(internal)"] = self.meta.pop("Orbit Z")

        # Reinitialize orbit containers for external data
        self.meta["Orbit Time"] = []
        self.meta["Orbit X"] = []
        self.meta["Orbit Y"] = []
        self.meta["Orbit Z"] = []

        self._read_external_orbit(f_orbit)
        return self
    

    def usage(self):
        """Print usage information"""
        print("===========================================================")
        print("           TERESA - 国产卫星 SAR 图像配准工具")
        print("===========================================================")
        print("Software Name   : TERESA (Tool for Enhanced Registration of Earth SAR imagery Automatically)")
        print("Version         : v0.1.0")
        print("Release Date    : 2025-07-31")
        print("")
        print("Developed by    : APRILab (Applied Processing & Remote-sensing Intelligence Lab)")
        print("Affiliation     : 西北工业大学 电子信息学院")
        print("Website         : https://github.com/aprilab-dev")
        print("Contact Email   : yuxiao.qin@nwpu.edu.cn")
        print("")
        print("File Generated  : ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("File Type       : SAR Registration Metadata")
        print("Input Mission   : LuTan-1")
        print("")
        print("Description     : 本文件标记了配准处理过程，SAR 图像的基本信息等。")
        print("")
        print(" -----------------------------------------------------------")
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
        print(" -----------------------------------------------------------")


def lt1_dump_header2doris(source_meta_path, work_dir):
    result_file = os.path.join(work_dir, "slave.res")
    lt1 = LT1()
    lt1.meta["path"] = source_meta_path
    with open(result_file, "w") as f:
        with redirect_stdout(f):
            lt1.usage()
            lt1.read_meta().update_external_orbit().export2res()