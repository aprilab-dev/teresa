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

    def read_meta(self):
        """Formatting the meta."""

        query_list: dict = {
            # volume info
            "Volume file": self.meta["path"],
            "Volume_ID": "adsHeader//missionId",
            "Volume_identifier": "adsHeader//missionId",
            "Volume_set_identifier": "adsHeader//missionId",
            # mission info
            "(Check)Number of records in ref. file": "imageAnnotation//imageInformation//numberOfLines",
            "SAR_PROCESSOR": None,
            "Product type specifier": "adsHeader//missionId",
            "Logical volume generating facility": None,
            "Logical volume creation date": None,
            "Location and date/time of product creation": None,
            "Orbit": "adsHeader//absoluteOrbitNumber",  # Scene identification
            "Direction": "generalAnnotation//productInformation//pass",  # Scene identification
            "Mode": "adsHeader//mode",  # Scene identification
            "Leader file": self.meta["path"],
            "Sensor platform mission identifer": "adsHeader//missionId",
            "Scene_centre_latitude": None,  # Scene location
            "Scene_centre_longitude": None,  # Scene location
            # product info
            "Radar_wavelength (m)": "generalAnnotation//productInformation//radarFrequency",
            "First_pixel_azimuth_time (UTC)": "imageAnnotation//imageInformation//productFirstLineUtcTime",
            "Last_pixel_azimuth_time (UTC)": "imageAnnotation//imageInformation//productLastLineUtcTime",
            "Pulse_Repetition_Frequency (computed, Hz)": "generalAnnotation//downlinkInformationList//prf",
            "Total_azimuth_band_width (Hz)": "imageAnnotation//processingInformation//swathProcParamsList//swathProcParams//azimuthProcessing//totalBandwidth",
            "Weighting_azimuth": None,
            "Doppler_Coef": "dopplerCentroid//dcEstimateList//dcEstimate//dataDcPolynomial",
            "Xtrack_f_DC_constant (Hz, early edge)": None,
            "Xtrack_f_DC_linear (Hz/s, early edge)": None,
            "Xtrack_f_DC_quadratic (Hz/s/s, early edge)": None,  # are all together
            "Range_time_to_first_pixel (2way) (ms)": "imageAnnotation//imageInformation//slantRangeTime",  # [s], needs to convert to ms
            "Range_sampling_rate (computed, MHz)": "generalAnnotation//productInformation//rangeSamplingRate",  # needs to divide by 1e6
            "Total_range_band_width (MHz)": "imageAnnotation//processingInformation//swathProcParamsList//swathProcParams//rangeProcessing//totalBandwidth",
            "Weighting_range": None,
            # SLC info
            "Datafile": None,
            "Dataformat": "adsHeader//productType",
            "Number_of_lines_original": "imageAnnotation//imageInformation//numberOfLines",
            "Number_of_pixels_original": "imageAnnotation//imageInformation//numberOfSamples",
            # Orbit
            "Orbit Time": "generalAnnotation//orbitList//orbit//time",
            "Orbit X": "generalAnnotation//orbitList//orbit//position//x",
            "Orbit Y": "generalAnnotation//orbitList//orbit//position//y",
            "Orbit Z": "generalAnnotation//orbitList//orbit//position//z",
            # Geolocation
            "latitude":"geolocationGrid//geolocationGridPointList//latitude",
            "longitude":"geolocationGrid//geolocationGridPoint//longitude",
        }

        # get variables and parameters from xml
        container: Dict[str, Any] = {
            "Orbit Time": [],
            "Orbit X": [],
            "Orbit Y": [],
            "Orbit Z": [],
            "latitude": [],
            "longitude": [],
        }
        root = ElementTree.parse(self.meta["path"]).getroot()
        for key, value in query_list.items():
            if value is None:
                container[key] = "Unknown"
            elif value.endswith(".xml"):  # metafile
                container[key] = os.path.basename(value)
            else:
                for item in root.findall(value):
                    # for item in root.findall(value):
                    if key.startswith("Orbit "):  # space is necessary here.
                        container[key].append(item.text)
                    elif key.endswith("tude") and key.startswith("l"): # latitude & longitude
                        container[key].append(item.text)
                    else:
                        container[key] = item.text

        # Two entries that have to be manually updated
        container["Orbit_n_pts"] = len(container["Orbit Time"])

        # center of the scene
        # find the 'geolocationGridPointList' element
        geolocation_list = root.find('geolocationGrid//geolocationGridPointList')
        count = geolocation_list.get('count')  # type: ignore
        center_scene_index = (int(count) + 1) // 2  # type: ignore
        container["Scene_centre_latitude"] = float(container["latitude"][center_scene_index])
        container["Scene_centre_longitude"] = float(container["longitude"][center_scene_index])

        container["Scene identification"] = (
            "Orbit: "
            + container["Orbit"]
            + " "
            + container["Direction"]
            + " Mode: "
            + container["Mode"]
        )
        container["Scene location"] = (
            "lat: "
            + str(container["Scene_centre_latitude"])  # type: ignore
            + " lon: "
            + str(container["Scene_centre_longitude"])
        )

        container["Datafile"] = os.path.basename(
            locate("bc*slc*.tiff", os.path.dirname(self.meta["path"]))
        )

        # 2-way Slant Range Time
        container["Range_time_to_first_pixel (2way) (ms)"] = (  # us to ms
            1000 * float(container["Range_time_to_first_pixel (2way) (ms)"])
        )

        # RSR
        container["Range_sampling_rate (computed, MHz)"] = (
            float(container["Range_sampling_rate (computed, MHz)"]) / 1e6
        )
        container["Total_range_band_width (MHz)"] = (
            float(container["Total_range_band_width (MHz)"]) / 1e6
        )

        container["Radar_wavelength (m)"] = SPEED_OF_LIGHT / float(container["Radar_wavelength (m)"])

        # unpack doppler coefficients
        (
            container["Xtrack_f_DC_constant (Hz, early edge)"],
            container["Xtrack_f_DC_linear (Hz/s, early edge)"],
            container["Xtrack_f_DC_quadratic (Hz/s/s, early edge)"], *_
        ) = container["Doppler_Coef"].split()

        # # First Line UTC Time
        # container["First_pixel_azimuth_time (UTC)"] = (
        #     datetime.strftime(
        #         datetime.strptime(
        #             container["First_pixel_azimuth_time (UTC)"],
        #             "%Y-%m-%dT%H:%M:%S.%f"
        #         ),
        #         "%d-%b-%Y %H:%M:%S.%f"
        #     )
        # )

        # update the time format
        cur_time = datetime.strptime(container["First_pixel_azimuth_time (UTC)"], "%Y-%m-%dT%H:%M:%S.%f")
        if container["Direction"] == "ASCENDING":
            cur_time = datetime.strptime(container["Last_pixel_azimuth_time (UTC)"], "%Y-%m-%dT%H:%M:%S.%f")
            cur_time = reverse_time(cur_time)  # reverse time to "fake" right looking
        container["First_pixel_azimuth_time (UTC)"] = (
            datetime.strftime(cur_time, "%d-%b-%Y %H:%M:%S.%f")
        )

        # manually update
        container["SAR_PROCESSOR"] = "HL"
        container["Logical volume generating facility"] = "HL"

        container["Product type specifier"] = "BC3"
        container["Sensor platform mission identifer"] = "BC3"

        self.meta.update(container)

        return self

    def export2res(self) -> None:
        """EXPORT2RES exports the meta into .res format that's compatible with doris."""
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

        print("\nbc3_dump_header2doris.py v1,0, doris software, 2024\n")
        print("**************************************************************")
        print("*_Start_readfiles:")
        print("**************************************************************")

        for keys in keys_lead:
            print("{:<50}\t{}".format(keys + ":", self.meta[keys]))

        print("")
        print("**************************************************************")
        for keys in keys_file:
            print("{:<50}\t{}".format(keys + ":", self.meta[keys]))

        print("**************************************************************")
        print("* End_readfiles:_NORMAL")
        print("**************************************************************")
        print("")
        print("")
        print("**************************************************************")
        print("*_Start_leader_datapoints")
        print("**************************************************************")
        print(" t(s)		X(m)		Y(m)		Z(m)")
        print("NUMBER_OF_DATAPOINTS: 			{}".format(self.meta["Orbit_n_pts"]))  # nopep8
        print("")

        if self.meta["Direction"] == "ASCENDING":  # fake right looking
            for i in reversed(range(0, self.meta["Orbit_n_pts"])):

                x, y, z = [
                    e
                    for e in (
                        self.meta["Orbit X"][i],
                        self.meta["Orbit Y"][i],
                        self.meta["Orbit Z"][i],
                    )
                ]  # format in a nicer way
                cur_orb_time = self.meta["Orbit Time"][i]
                cur_orb_time = reverse_time(datetime.strptime(cur_orb_time, "%Y-%m-%dT%H:%M:%S.%f"))
                cur_orb_time = datetime.strftime(cur_orb_time, "%Y-%m-%dT%H:%M:%S.%f")
                print(
                    " {:>7} {:>15} {:>15} {:>15}".format(
                        hms2sec(cur_orb_time, convertFlag="float"),
                        x,
                        y,
                        z
                    )
                )
        else:
            for i in range(0, self.meta["Orbit_n_pts"]):

                x, y, z = [
                    e
                    for e in (
                        self.meta["Orbit X"][i],
                        self.meta["Orbit Y"][i],
                        self.meta["Orbit Z"][i],
                    )
                ]  # format in a nicer way

                cur_orb_time = self.meta["Orbit Time"][i]
                print(
                    " {:>7} {:>15} {:>15} {:>15}".format(
                        hms2sec(cur_orb_time, convertFlag="float"),
                        x,
                        y,
                        z
                    )
                )

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
            bc.read_meta().export2res()