#!/usr/bin/env python3
"""
Geocoding with DEM - Python Implementation

Converts radar coordinates (line, pixel) with DEM heights to
geographic coordinates (latitude, longitude) using precise orbit data.

Based on Doris Radar Coding C++ implementation.
Integrates with orbit interpolation module for precise coordinate transformation.

Author: X.W, 2025
Original: Delft University of Technology
"""

import os
import re
import sys
import glob
import yaml
import time
import math
import threading
import numpy as np
import multiprocessing as mp
from numba import njit, jit, prange
from functools import partial
from scipy.interpolate import RegularGridInterpolator
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from .dataclass import ImageGeometry, DEMGeometry, ProductInfo
from ._orbit import (
    SOL, Point3D, Ellipsoid, Orbit,
    eq1_doppler, eq2_range,
    eq3_ellipsoid, solve33,
    _print, set_log_file)

_log_file = None


@dataclass
class ForwardGeocodeInput:
    """Geocoding input/output parameters"""
    dem_file: str
    output_phi: str
    output_lambda: str
    dem_format: str = "real4"
    fihei: str = None  # Input DEM file path (if different from dem_file)


def parse_doris_datetime(datetime_str: str) -> datetime:
    """
    Parse a Doris datetime string into a Python datetime object.

    Args:
        datetime_str: Input datetime string in Doris format.

    Returns:
        parsed_datetime: Parsed datetime value.
    """
    if not isinstance(datetime_str, str):
        raise TypeError("Input must be a string")

    datetime_str = datetime_str.strip()
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_to_num = {name: i + 1 for i, name in enumerate(months)}

    try:
        # Split date and time fields.
        date_part, time_part = datetime_str.split(" ", 1)
        day_str, mon_str, year_str = date_part.split("-")
        day = int(day_str)
        year = int(year_str)
        month = month_to_num[mon_str]  # KeyError if invalid

        # Parse time part (including microseconds).
        if "." in time_part:
            time_str, micro_str = time_part.split(".", 1)
            microsecond = int(micro_str.ljust(6, "0")[:6])  # Pad to 6 digits then truncate.
        else:
            time_str = time_part
            microsecond = 0

        hour, minute, second = map(int, time_str.split(":"))
        return datetime(year, month, day, hour, minute, second, microsecond)
    except (ValueError, KeyError, IndexError):
        raise ValueError(f"Cannot parse datetime string: {repr(datetime_str)}")


def format_doris_datetime(dt: datetime) -> str:
    """
    Format a datetime object into Doris datetime string format.

    Args:
        dt: Input datetime object.

    Returns:
        datetime_str: Formatted datetime string.
    """
    # return dt.strftime("%d-%b-%Y %H:%M:%S.%f")[:-3]  # Keep 3 decimal places.
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    # Keep 3 decimal places.
    return f"{dt.day:02d}-{months[dt.month - 1]}-{dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.{dt.microsecond:06d}"[:-3]


def multilook_array(arr: np.ndarray, alooks: int, rlooks: int) -> np.ndarray:
    """
    Apply multilooking using NaN-safe block averaging.

    Args:
        arr: Input 2D array with shape [H, W].
        alooks: Number of looks in azimuth (rows).
        rlooks: Number of looks in range (columns).

    Returns:
        multilooked_arr: Output array with shape [H//alooks, W//rlooks].
    """
    H, W = arr.shape
    H_ml = (H // alooks) * alooks
    W_ml = (W // rlooks) * rlooks
    arr_crop = arr[:H_ml, :W_ml]
    arr_reshaped = arr_crop.reshape(H_ml // alooks, alooks, W_ml // rlooks, rlooks)
    return np.nanmean(arr_reshaped, axis=(1, 3))

# ------------------------------------------------------------------------
# Doris Result File Parser
# ------------------------------------------------------------------------


class DorisResParser:
    """Parser for Doris .res files."""

    @staticmethod
    def parse_res_file(res_file: str) -> Dict[str, Any]:
        """
        
            Parse a Doris .res file and collect parameters.

        Args:
            res_file: Path to the Doris .res file.

        Returns:
            parameters: Parsed parameter dictionary.
        """
        parameters = {}

        try:
            with open(res_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Parse all parameter sections.
            parameters.update(DorisResParser._parse_general_parameters(content))
            parameters.update(DorisResParser._parse_geo_parameters(content))
            parameters.update(DorisResParser._parse_time_parameters(content))
            parameters.update(DorisResParser._parse_orbit_parameters(content))

            _print(f"Successfully parsed res file: {res_file}")
            return parameters

        except Exception as e:
            _print(f"Error parsing res file {res_file}: {e}")
            return {}

    @staticmethod
    def _parse_general_parameters(content: str) -> Dict[str, Any]:
        """
        Parse general image and acquisition parameters from res content.

        Args:
            content: Full text content of a Doris .res file.

        Returns:
            params: Dictionary of parsed general parameters.
        """
        params = {}

        # Image dimensions.
        match = re.search(r'Number_of_lines_original:\s*(\d+)', content)
        if match:
            params['naz_original'] = int(match.group(1))

        match = re.search(r'Number_of_pixels_original:\s*(\d+)', content)
        if match:
            params['nr_original'] = int(match.group(1))

        # Match First/Last pixel/line regardless of text inside parentheses.
        match = re.findall(r'First_pixel\s*\(.*?\):\s*(\d+)', content)
        if match:
            params['first_pixel'] = int(match[-1])

        match = re.findall(r'Last_pixel\s*\(.*?\):\s*(\d+)', content)
        if match:
            params['last_pixel'] = int(match[-1])

        match = re.findall(r'First_line\s*\(.*?\):\s*(\d+)', content)
        if match:
            params['first_line'] = int(match[-1])

        match = re.findall(r'Last_line\s*\(.*?\):\s*(\d+)', content)
        if match:
            params['last_line'] = int(match[-1])

        # Range and azimuth parameters.
        match = re.search(r'Range_pixel_spacing:\s*([\d.]+)', content)
        if match:
            params['range_pixel_spacing'] = float(match.group(1))

        match = re.search(r'Azimuth_pixel_spacing:\s*([\d.]+)', content)
        if match:
            params['azimuth_pixel_spacing'] = float(match.group(1))

        match = re.search(r'PRF.*\(Hz\):\s*([\d.]+)', content)
        if match:
            params['prf'] = float(match.group(1))

        match = re.search(r'Terrain_height:\s*([\d.-]+)', content)
        if match:
            params['terrain_height'] = float(match.group(1))

        # Parse antenna side (look direction)
        match = re.search(r'Antenna_side:\s*(left|right)', content, re.IGNORECASE)
        if match:
            params['antenna_side'] = match.group(1).lower()
            _print(f"Found Antenna side: {params['antenna_side']}")

        # Parse incidence angle
        match = re.search(r'Incidence_angle_mid_swath:\s*([\d.]+)', content)
        if match:
            params['incidence_angle'] = float(match.group(1))
            _print(f"Found Incidence angle: {params['incidence_angle']} degrees")

        return params

    @staticmethod
    def _parse_geo_parameters(content: str) -> Dict[str, Any]:
        """
        Parse geographic and geodetic parameters from res content.

        Args:
            content: Full text content of a Doris .res file.

        Returns:
            params: Dictionary of parsed geographic parameters.
        """
        params = {}

        # Parse Scene location (format: "Scene location: lat: 35.0253 lon: 117.0365").
        match = re.search(r'Scene location:\s*lat:\s*([\d.-]+)\s*lon:\s*([\d.-]+)', content)
        if match:
            params['scene_location_lat'] = float(match.group(1))
            params['scene_location_lon'] = float(match.group(2))
            _print(f"Found Scene location: lat={params['scene_location_lat']}, lon={params['scene_location_lon']}")

        # Parse Scene_centre_latitude (format: "Scene_centre_latitude: 35.0253").
        match = re.search(r'Scene_centre_latitude:\s*([\d.-]+)', content)
        if match:
            params['scene_center_lat'] = float(match.group(1))
            _print(f"Found Scene_centre_latitude: {params['scene_center_lat']}")

        # Parse Scene_centre_longitude (format: "Scene_centre_longitude: 117.0365").
        match = re.search(r'Scene_centre_longitude:\s*([\d.-]+)', content)
        if match:
            params['scene_center_lon'] = float(match.group(1))
            _print(f"Found Scene_centre_longitude: {params['scene_center_lon']}")

        # Parse Scene_corner_latitude (format: "Scene_corner_latitude: [34.9001, 34.8452, 34.6814, 34.6266]").
        match = re.search(r'Scene_corner_latitude:\s*\[([\d.,\s-]+)\]', content)
        if match:
            corner_lats_str = match.group(1)
            try:
                corner_lats = [float(x.strip()) for x in corner_lats_str.split(',')]
                params['scene_corner_lat'] = corner_lats
                _print(f"Found Scene_corner_latitude: {corner_lats}")
            except ValueError as e:
                _print(f"Warning: Could not parse Scene_corner_latitude: {e}")

        # Parse Scene_corner_longitude (format: "Scene_corner_longitude: [116.7102, 116.983, 116.6466, 116.9187]").
        match = re.search(r'Scene_corner_longitude:\s*\[([\d.,\s-]+)\]', content)
        if match:
            corner_lons_str = match.group(1)
            try:
                corner_lons = [float(x.strip()) for x in corner_lons_str.split(',')]
                params['scene_corner_lon'] = corner_lons
                _print(f"Found Scene_corner_longitude: {corner_lons}")
            except ValueError as e:
                _print(f"Warning: Could not parse Scene_corner_longitude: {e}")

        # Parse scene identification (format: "Scene identification: Orbit: 8792 DESCENDING Mode: S1").
        match = re.search(r'Scene identification:\s*(.+)', content)
        if match:
            params['scene_identification'] = match.group(1).strip()
            _print(f"Found Scene identification: {params['scene_identification']}")

        # Parse radar wavelength (format: "Radar_wavelength (m): 0.055517120823757024").
        match = re.search(r'Radar_wavelength.*\(m\):\s*([\d.]+)', content)
        if match:
            params['radar_wavelength'] = float(match.group(1))
            _print(f"Found Radar wavelength: {params['radar_wavelength']} m")

        # Parse Earth ellipsoid parameters.
        match = re.search(r'Reference_range:\s*([\d.]+)', content, re.IGNORECASE)
        if match:
            params['reference_range'] = float(match.group(1))

        match = re.search(r'Ellipsoid_semi_major_axis:\s*([\d.]+)', content, re.IGNORECASE)
        if match:
            params['earth_major_axis'] = float(match.group(1))

        match = re.search(r'Ellipsoid_semi_minor_axis:\s*([\d.]+)', content, re.IGNORECASE)
        if match:
            params['earth_minor_axis'] = float(match.group(1))

        return params

    @staticmethod
    def _parse_time_parameters(content: str) -> Dict[str, Any]:
        """
        Parse imaging time and frequency parameters from res content.

        Args:
            content: Full text content of a Doris .res file.

        Returns:
            params: Dictionary of parsed time-related parameters.
        """
        params = {}

        # Parse azimuth time of the first pixel.
        match = re.search(r'First_pixel_azimuth_time.*?UTC\):\s*([^\n]+)', content)
        if match:
            time_str = match.group(1).strip()
            params['first_pixel_time'] = time_str
            params['first_pixel_datetime'] = parse_doris_datetime(time_str)
            _print(f"Found First pixel azimuth time: {params['first_pixel_time']}")

        # Parse azimuth time of the last pixel.
        match = re.search(r'Last_pixel_azimuth_time.*?UTC\):\s*([^\n]+)', content)
        if match:
            time_str = match.group(1).strip()
            params['last_pixel_time'] = time_str
            params['last_pixel_datetime'] = parse_doris_datetime(time_str)
            _print(f"Found Last pixel azimuth time: {params['last_pixel_time']}")

        # Pulse repetition frequency.
        match = re.search(r'Pulse_Repetition_Frequency.*\(computed, Hz\):\s*([\d.]+)', content)
        if match:
            params['prf_computed'] = float(match.group(1))
            _print(f"Found PRF (computed): {params['prf_computed']} Hz")

        # Parse total azimuth bandwidth.
        match = re.search(r'Total_azimuth_band_width.*\(Hz\):\s*([\d.]+)', content)
        if match:
            params['total_azimuth_bandwidth'] = float(match.group(1))
            _print(f"Found Total azimuth bandwidth: {params['total_azimuth_bandwidth']} Hz")

        # Parse range time to first pixel.
        match = re.search(r'Range_time_to_first_pixel.*\(2way\).*\(ms\):\s*([\d.]+)', content)
        if match:
            params['range_time_to_first_pixel'] = float(match.group(1))
            _print(f"Found Range time to first pixel: {params['range_time_to_first_pixel']} ms")

        # Parse range sampling rate.
        match = re.search(r'Range_sampling_rate.*\(computed, MHz\):\s*([\d.]+)', content)
        if match:
            params['range_sampling_rate'] = float(match.group(1))
            _print(f"Found Range sampling rate: {params['range_sampling_rate']} MHz")

        # Parse total range bandwidth.
        match = re.search(r'Total_range_band_width.*\(MHz\):\s*([\d.]+)', content)
        if match:
            params['total_range_bandwidth'] = float(match.group(1))
            _print(f"Found Total range bandwidth: {params['total_range_bandwidth']} MHz")

        return params

    @staticmethod
    def _parse_orbit_parameters(content: str) -> Dict[str, Any]:
        """
        Parse orbit parameters and leader datapoints from res content.

        Args:
            content: Full text content of a Doris .res file.

        Returns:
            params: Dictionary of parsed orbit-related parameters.
        """
        params = {}
        orbit_data = []

        # Parse orbit datapoints section.
        orbit_points_section = re.search(
            r'\*_Start_leader_datapoints\b.*?\* End_leader_datapoints:_NORMAL',
            content, re.DOTALL
        )

        if orbit_points_section:
            points_text = orbit_points_section.group(0)
            lines = points_text.split('\n')

            # Skip headers and parse only data rows.
            data_started = False
            for line in lines:
                # Skip header and separator lines.
                if not data_started and ('t(s)' in line or 'NUMBER_OF_DATAPOINTS' in line):
                    continue
                if '*_Start_leader_datapoints:' in line or '* End_leader_datapoints:' in line:
                    continue

                match = re.match(
                    r'\s*([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)(?:\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+))?', line.strip())
                if match:
                    groups = match.groups()
                    time, x, y, z = map(float, groups[0:4])

                    # Check whether VX/VY/VZ values exist.
                    if groups[4] and groups[5] and groups[6]:
                        vx, vy, vz = map(float, groups[4:7])
                        orbit_data.append((time, x, y, z, vx, vy, vz))
                    else:
                        orbit_data.append((time, x, y, z))

                    data_started = True

            params['orbit_data'] = orbit_data
            has_velocity = len(orbit_data) > 0 and len(orbit_data[0]) == 7
            _print(f"Found {len(orbit_data)} orbit data points" +
                   (" with velocity data" if has_velocity else ""))

        # Parse number of orbit records.
        match = re.search(r'\(Check\)Number of records in ref\. file:\s*(\d+)', content)
        if match:
            params['orbit_records_count'] = int(match.group(1))
            _print(f"Found number of orbit records: {params['orbit_records_count']}")

        # Parse additional orbit-related parameters.
        match = re.search(r'Volume_ID:\s*(\S+)', content)
        if match:
            params['volume_id'] = match.group(1).strip()
            _print(f"Found Volume ID: {params['volume_id']}")

        match = re.search(r'Sensor platform mission identifer:\s*(\S+)', content)
        if match:
            params['sensor_platform'] = match.group(1).strip()
            _print(f"Found Sensor platform: {params['sensor_platform']}")

        return params

# ------------------------------------------------------------------------
# Geocoding Processor - Generate LUT for Geocoding with DEM
# ------------------------------------------------------------------------


class GeocodingProcessor:
    """
    Main geocoding processor class

    Transforms DEM in radar coordinates to geographic coordinates
    using precise orbit information and zero-Doppler geometry.
    """

    def __init__(self, memory_mb: int = None, n_workers: Optional[int] = None, log_file: Optional[str] = None):
        """
        Initialize the geocoding processor.

        Args:
            memory_mb: Available memory for buffers [MB]
            n_workers: Number of worker processes.
            log_file: Optional log file path

        Returns:
            result: None.
        """
        self.MAXITER = 100  # Maximum iterations for lp2xyz
        self.CRITERPOS = 1e-6  # Convergence criterion [m]
        if memory_mb is None:
            import psutil
            available_memory_bytes = psutil.virtual_memory().available
            available_memory_mb = available_memory_bytes / (1024 * 1024)
            self.memory_mb = max(100, int(available_memory_mb // 2))  # Half, minimum 100MB
            _print(f"Auto-detected {available_memory_mb:.0f} MB available RAM, using {self.memory_mb} MB for buffers")
        else:
            self.memory_mb = max(100, memory_mb)
            _print(f"Using {self.memory_mb} MB for buffers (user-specified)")

        # self.n_workers = n_workers or max(1, mp.cpu_count() - 1)
        if n_workers is None:
            total_cpus = mp.cpu_count()
            self.n_workers = max(1, total_cpus // 2)  # Half of CPUs, minimum 1
            # self.n_workers = max(1, total_cpus - 1)  # All but one CPU
            _print(f"Auto-detected {total_cpus} CPU cores, using {self.n_workers} workers")
        else:
            self.n_workers = max(1, n_workers)
            _print(f"Using {self.n_workers} workers (user-specified)")

        if log_file:
            set_log_file(log_file)

    def create_lut_forwardgeocode(self,
                                  dem_radar: np.ndarray,
                                  orbit: 'Orbit',
                                  image_geom: 'ImageGeometry',
                                  product_info: 'ProductInfo',
                                  geocode_input: 'ForwardGeocodeInput',
                                  ellipsoid: Optional['Ellipsoid'] = None,
                                  overwrite: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Perform fast DEM-based forward geocoding using Numba.
        This implementation follows the lph2xyz reference behavior.

        Args:
            dem_radar: Multilooked DEM in radar coordinates [H, W]
            orbit: Orbit object with get_xyz(t) and get_xyz_dot(t)
            image_geom: ImageGeometry with line2ta(line) method
            product_info: ProductInfo with necessary metadata
            geocode_input: ForwardGeocodeInput with output paths
            ellipsoid: Optional Ellipsoid object (defaults to WGS84)
            overwrite: Whether to overwrite existing output files

        Returns:
            geocode_lut: Tuple (PHI, LAMBDA) in degrees.
        """

        _print("="*70)
        _print("GEOCODING WITH DEM - Numba (lph2xyz algorithm)")
        _print("="*70)

        if ellipsoid is None:
            ellipsoid = Ellipsoid()

        _print(f"Using ellipsoid: {ellipsoid.name}")
        _print(f"a = {ellipsoid.a:.3f} m, b = {ellipsoid.b:.3f} m")

        # Multilook factors
        multiL = float(product_info.multilook_L)
        multiP = float(product_info.multilook_P)
        _print(f"Multilook factors: azimuth={multiL}, range={multiP}")

        # Get multilooked dimensions
        ml_lines, ml_pixels = dem_radar.shape
        _print(f"Multilooked DEM dimensions: {ml_lines} lines x {ml_pixels} pixels")

        # Line/pixel of first point in original master coordinates
        # very_first_line = float(product_info.line_start) + (multiL - 1.0) / 2.0
        # first_pixel = float(product_info.pixel_start) + (multiP - 1.0) / 2.0
        very_first_line = 0.0
        first_pixel = 0.0
        _print(f"First line in master coordinates: {very_first_line:.2f}")
        _print(f"First pixel in master coordinates: {first_pixel:.2f}")

        # Pre-compute orbit state vectors for all lines
        unique_lines = np.arange(ml_lines) * multiL + very_first_line
        az_times = np.array([image_geom.line2ta(line) for line in unique_lines])

        # Cache orbit data
        n_orbit_points = len(az_times)
        orbit_pos = np.zeros((n_orbit_points, 3))
        orbit_vel = np.zeros((n_orbit_points, 3))

        _print("Pre-computing orbit state vectors...")
        for i, t in enumerate(az_times):
            pos = orbit.get_xyz(t)
            vel = orbit.get_xyz_dot(t)
            orbit_pos[i] = [pos.x, pos.y, pos.z]
            orbit_vel[i] = [vel.x, vel.y, vel.z]

        # Compute scene center for initial guess
        image_center_line = very_first_line + (ml_lines / 2.0) * multiL
        image_center_pixel = first_pixel + (ml_pixels / 2.0) * multiP
        center_az_time = image_geom.line2ta(image_center_line)
        image_center_pos = orbit.get_xyz(center_az_time)
        image_center_vel = orbit.get_xyz_dot(center_az_time)

        # Get look side from image geometry.
        look_side = getattr(image_geom, 'antenna_side', 'right').lower()  # 'left' or 'right'
        look_sign = -1.0 if look_side == 'left' else 1.0  # Left = -1, Right = +1

        _print(f"Antenna side: {look_side} (look_sign={look_sign})")

        # Use center pixel range to compute initial scene position
        center_pixel = first_pixel + (ml_pixels / 2.0) * multiP
        center_range_time = image_geom.near_range_time + center_pixel * image_geom.pixel_time_interval
        center_slant_range = SOL * center_range_time / 2.0  # Two-way to one-way distance

        _print(f"Center pixel: {center_pixel:.2f}")
        _print(f"Center range time (2-way): {center_range_time*1000:.6f} ms")
        _print(f"Center slant range (1-way): {center_slant_range:.2f} m")

        if hasattr(image_geom, 'scene_center_lat') and hasattr(image_geom, 'scene_center_lon'):
            center_lat = np.radians(image_geom.scene_center_lat)
            center_lon = np.radians(image_geom.scene_center_lon)

            # Use average terrain height or 0
            center_height = getattr(image_geom, 'terrain_height', 0.0)

            _print(
                f"Using scene center from res file: lat={image_geom.scene_center_lat:.4f}°, lon={image_geom.scene_center_lon:.4f}°")

            # Convert LLA to ECEF
            sin_lat = np.sin(center_lat)
            cos_lat = np.cos(center_lat)
            sin_lon = np.sin(center_lon)
            cos_lon = np.cos(center_lon)

            N = ellipsoid.a / np.sqrt(1.0 - ellipsoid.e2 * sin_lat**2)

            scene_center_x = (N + center_height) * cos_lat * cos_lon
            scene_center_y = (N + center_height) * cos_lat * sin_lon
            scene_center_z = ((1.0 - ellipsoid.e2) * N + center_height) * sin_lat

            _print(f"Scene center XYZ from res: ({scene_center_x:.2f}, {scene_center_y:.2f}, {scene_center_z:.2f})")
        else:
            _print("WARNING: No scene center in res file, using geometric calculation")
            # Build coordinate system at satellite
            sat_pos = np.array([image_center_pos.x, image_center_pos.y, image_center_pos.z])
            sat_vel = np.array([image_center_vel.x, image_center_vel.y, image_center_vel.z])

            # Flight direction (along-track): normalized velocity
            along_track = sat_vel / np.linalg.norm(sat_vel)

            # Radial direction (toward Earth center)
            radial = -sat_pos / np.linalg.norm(sat_pos)

            # Cross-track direction (perpendicular to both flight and radial)
            # Right-hand rule: for descending orbit (moving south), right side = east
            cross_track = np.cross(sat_vel, radial)  # velocity × radial_down
            cross_track = cross_track / np.linalg.norm(cross_track)

            # For left-looking, flip the direction
            # if look_side == 'left':
            #     cross_track = -cross_track

            _print(f"Cross-track vector: ({cross_track[0]:.3f}, {cross_track[1]:.3f}, {cross_track[2]:.3f})")

            # Look vector: combination of cross-track and radial
            incidence_angle_deg = getattr(image_geom, 'incidence_angle', 30.0)
            incidence_angle = np.radians(incidence_angle_deg)

            _print(f"Incidence angle: {incidence_angle_deg:.2f} degrees")

            # Look vector from satellite to ground
            # sin(incidence) component in cross-track, cos(incidence) component radial (downward)
            look_vector = np.sin(incidence_angle) * cross_track + np.cos(incidence_angle) * radial

            # Initial scene center position
            scene_center_xyz = sat_pos + center_slant_range * look_vector

            scene_center_x = scene_center_xyz[0]
            scene_center_y = scene_center_xyz[1]
            scene_center_z = scene_center_xyz[2]

            _print(f"Satellite position: ({sat_pos[0]:.2f}, {sat_pos[1]:.2f}, {sat_pos[2]:.2f})")
            _print(f"Scene center XYZ: ({scene_center_x:.2f}, {scene_center_y:.2f}, {scene_center_z:.2f})")

            # Verify: compute lat/lon of initial guess
            scene_r = np.sqrt(scene_center_x**2 + scene_center_y**2)
            scene_lat_init = np.degrees(np.arctan2(scene_center_z, scene_r * (1 - ellipsoid.e2)))
            scene_lon_init = np.degrees(np.arctan2(scene_center_y, scene_center_x))
            scene_height_init = np.linalg.norm(scene_center_xyz) - ellipsoid.a
            _print(f"Initial guess: lat={scene_lat_init:.4f}°, lon={scene_lon_init:.4f}°, h={scene_height_init:.1f}m")

        _print(f"Expected from res: lat={image_geom.scene_center_lat:.4f}°, lon={image_geom.scene_center_lon:.4f}°")
        # Numba-accelerated core computation

        @jit(nopython=True, parallel=True, fastmath=True)
        def compute_geocoding_core(dem, orbit_pos_arr, orbit_vel_arr,
                                   first_line, first_pix, multiL, multiP,
                                   near_range_t, pixel_time_int,
                                   ell_a, ell_b, ell_e2, ell_e2b,
                                   scene_x, scene_y, scene_z,
                                   max_iter, criter, sol):
            """
            Compute geocoding latitude/longitude arrays in the Numba kernel.

            Args:
                dem: DEM grid in radar coordinates.
                orbit_pos_arr: Satellite position array per azimuth line.
                orbit_vel_arr: Satellite velocity array per azimuth line.
                first_line: First line index in source geometry.
                first_pix: First pixel index in source geometry.
                multiL: Azimuth multilook factor.
                multiP: Range multilook factor.
                near_range_t: Near range time in seconds.
                pixel_time_int: Pixel time interval in seconds.
                ell_a: Ellipsoid semi-major axis.
                ell_b: Ellipsoid semi-minor axis.
                ell_e2: First eccentricity squared.
                ell_e2b: Second eccentricity squared.
                scene_x: Initial scene center X in ECEF.
                scene_y: Initial scene center Y in ECEF.
                scene_z: Initial scene center Z in ECEF.
                max_iter: Maximum iteration count.
                criter: Convergence threshold.
                sol: Speed of light constant.

            Returns:
                geocode_core_result: Tuple (phi, lam) in degrees.
            """
            lines, pixels = dem.shape
            phi = np.full((lines, pixels), np.nan, dtype=np.float32)
            lam = np.full((lines, pixels), np.nan, dtype=np.float32)

            for i in prange(lines):
                # Get orbit state for this line
                pos_sat = orbit_pos_arr[i]
                vel_sat = orbit_vel_arr[i]

                for j in range(pixels):
                    height = dem[i, j]
                    if np.isnan(height) or np.isinf(height):
                        continue

                    # Calculate pixel and range time
                    pixel = first_pix + j * multiP
                    # Try WITHOUT the -1.0 offset (C++ might not use it)
                    range_time = near_range_t + pixel * pixel_time_int

                    # Elevated ellipsoid parameters
                    a_elev = ell_a + height
                    b_elev = ell_b + height

                    # Initial guess: scene center (matches lph2xyz)
                    posonellx = scene_x
                    posonelly = scene_y
                    posonellz = scene_z

                    # Newton-Raphson iteration
                    for iteration in range(max_iter):
                        # Vector from satellite to point
                        dsat_Px = posonellx - pos_sat[0]
                        dsat_Py = posonelly - pos_sat[1]
                        dsat_Pz = posonellz - pos_sat[2]

                        # Evaluate equations (NEGATED - matches lph2xyz)
                        # 1. Doppler equation
                        f1 = -(vel_sat[0]*dsat_Px + vel_sat[1]*dsat_Py + vel_sat[2]*dsat_Pz)

                        # 2. Range equation
                        # CRITICAL: In lph2xyz, this is slant_range, NOT range_time
                        # slant_range = SOL * range_time (one-way)
                        # Test fix.
                        slant_range = sol * range_time / 2
                        f2 = -(dsat_Px*dsat_Px + dsat_Py*dsat_Py + dsat_Pz*dsat_Pz -
                               slant_range**2)

                        # 3. Ellipsoid equation (matches lph2xyz format exactly)
                        f3 = -((posonellx*posonellx + posonelly*posonelly) / (a_elev**2) +
                               (posonellz/b_elev)**2 - 1.0)

                        # Build Jacobian
                        J00 = vel_sat[0]
                        J01 = vel_sat[1]
                        J02 = vel_sat[2]

                        J10 = 2.0 * dsat_Px
                        J11 = 2.0 * dsat_Py
                        J12 = 2.0 * dsat_Pz

                        # KEY: Uses ELEVATED parameters (matches lph2xyz)
                        J20 = (2.0 * posonellx) / (a_elev**2)
                        J21 = (2.0 * posonelly) / (a_elev**2)
                        J22 = (2.0 * posonellz) / (b_elev**2)

                        # Solve using Cramer's rule: J * sol = equationset
                        det = (J00*(J11*J22 - J12*J21) -
                               J01*(J10*J22 - J12*J20) +
                               J02*(J10*J21 - J11*J20))

                        if abs(det) < 1e-20:
                            break

                        # Cramer's rule (solving J * [solx, soly, solz]^T = [f1, f2, f3]^T)
                        solx = (f1*(J11*J22 - J12*J21) -
                                J01*(f2*J22 - J12*f3) +
                                J02*(f2*J21 - J11*f3)) / det

                        soly = (J00*(f2*J22 - J12*f3) -
                                f1*(J10*J22 - J12*J20) +
                                J02*(J10*f3 - f2*J20)) / det

                        solz = (J00*(J11*f3 - f2*J21) -
                                J01*(J10*f3 - f2*J20) +
                                f1*(J10*J21 - J11*J20)) / det

                        # Update solution
                        posonellx += solx
                        posonelly += soly
                        posonellz += solz

                        # Check convergence
                        if abs(solx) < criter and abs(soly) < criter and abs(solz) < criter:
                            # Convert to lat/lon using Bowring's method
                            r = math.sqrt(posonellx**2 + posonelly**2)
                            mu = math.atan2(posonellz * ell_a, r * ell_b)

                            sin_mu = math.sin(mu)
                            cos_mu = math.cos(mu)
                            sin3 = sin_mu**3
                            cos3 = cos_mu**3

                            lat = math.atan2(
                                posonellz + ell_e2b * ell_b * sin3,
                                r - ell_e2 * ell_a * cos3
                            )
                            lon = math.atan2(posonelly, posonellx)

                            phi[i, j] = math.degrees(lat)
                            lam[i, j] = math.degrees(lon)
                            break

            return phi, lam

        _print("Running Numba-accelerated geocoding...")
        start_time = time.time()

        # Run computation
        PHI, LAMBDA = compute_geocoding_core(
            dem_radar.astype(np.float32),
            orbit_pos, orbit_vel,
            very_first_line, first_pixel,
            multiL, multiP,
            image_geom.near_range_time,
            image_geom.pixel_time_interval,
            ellipsoid.a, ellipsoid.b, ellipsoid.e2, ellipsoid.e2b,
            scene_center_x, scene_center_y, scene_center_z,
            self.MAXITER, self.CRITERPOS, SOL
        )

        elapsed_time = time.time() - start_time
        _print(f"Computation completed in {elapsed_time:.2f} seconds")
        _print(f"Processing rate: {ml_lines * ml_pixels / elapsed_time:.0f} points/second")

        # Check results
        valid_mask = np.isfinite(PHI) & np.isfinite(LAMBDA)
        valid_count = np.sum(valid_mask)
        total_count = PHI.size

        _print(f"Geocoding Results:")
        _print(f"Output grid shape: {PHI.shape}")

        if valid_count > 0:
            _print(f"Latitude range: [{np.nanmin(PHI):.6f}, {np.nanmax(PHI):.6f}] degrees")
            _print(f"Longitude range: [{np.nanmin(LAMBDA):.6f}, {np.nanmax(LAMBDA):.6f}] degrees")
            _print(f"Valid points: {valid_count} / {total_count} ({valid_count/total_count*100:.1f}%)")
        else:
            _print("WARNING: All outputs are NaN! Check:")
            _print("  1. DEM values are valid")
            _print("  2. Orbit data is correct")
            _print("  3. Image geometry parameters are correct")

        # Write output files
        _print("Writing output files...")
        if not overwrite:
            import os
            if os.path.exists(geocode_input.output_phi):
                raise FileExistsError(f"File exists: {geocode_input.output_phi}")
            if os.path.exists(geocode_input.output_lambda):
                raise FileExistsError(f"File exists: {geocode_input.output_lambda}")

        PHI.tofile(geocode_input.output_phi)
        _print(f"Data_output_file_phi: {geocode_input.output_phi}")

        LAMBDA.tofile(geocode_input.output_lambda)
        _print(f"Data_output_file_lambda: {geocode_input.output_lambda}")

        _print("="*70)
        _print("GEOCODING FINISHED")
        _print("="*70)

        return PHI, LAMBDA

# ------------------------------------------------------------------------
# Radar to Geographic Coordinate Converter
# ------------------------------------------------------------------------
# Use lat.rdr and lon.rdr to convert radar coordinates to geographic coordinates.
# Also use the lat.rdr and lon.rdr to search the corresponding pixel in geographic coordinates.
# TODO: add parser to backforward geocoding LUTs.

class RDCGEOConverter:
    def __init__(self, lat_lut: str, lon_lut: str, nlines: int, npixels: int):
        """
        Initialize a radar-to-geographic converter using forward LUT files.

        Args:
            lat_lut: Path to latitude LUT file.
            lon_lut: Path to longitude LUT file.
            nlines: Number of radar lines.
            npixels: Number of radar pixels.

        Returns:
            result: None.
        """
        self.nlines = nlines
        self.npixels = npixels
        self.lat_lut = read_dem_binary(lat_lut, self.nlines, self.npixels)
        self.lon_lut = read_dem_binary(lon_lut, self.nlines, self.npixels)
        if self.lat_lut.shape != self.lon_lut.shape:
            raise ValueError("Latitude and Longitude LUTs must have the same shape.")

    def radar_to_geo(self, line: int, pixel: int) -> Tuple[float, float]:
        """
        Convert radar coordinates to geographic coordinates.

        Args:
            line: Radar line index.
            pixel: Radar pixel index.

        Returns:
            lat_lon: Tuple (lat, lon) in degrees.
        """
        if line < 0 or line >= self.nlines or pixel < 0 or pixel >= self.npixels:
            raise IndexError("Radar coordinates out of bounds.")
        lat = self.lat_lut[line, pixel]
        lon = self.lon_lut[line, pixel]
        return lat, lon

    def geo_to_radar(self, lat: float, lon: float) -> Tuple[int, int]:
        """
        Convert geographic coordinates to the nearest radar coordinates.

        Args:
            lat: Latitude in degrees.
            lon: Longitude in degrees.

        Returns:
            line_pixel: Tuple (line, pixel) indices.
        """
        # Find the closest match in the LUTs
        lat_diff = np.abs(self.lat_lut - lat)
        lon_diff = np.abs(self.lon_lut - lon)
        total_diff = lat_diff + lon_diff
        idx = np.unravel_index(np.argmin(total_diff), total_diff.shape)
        return idx  # Returns (line, pixel)


class RDCGEOConverter_2:
    def __init__(self, ranpix: str, azpix: str, nlines: int, npixels: int):
        """
        Initialize a radar-to-geographic converter using backward LUT files.

        Args:
            ranpix: Path to longitude LUT(lookup_range.rdr)
            azpix: Path to latitude LUT(lookup_azimuth.rdr)
            nlines, npixels: Radar image dimensions

        Returns:
            result: None.
        """
        self.nlines = nlines
        self.npixels = npixels
        self.lon_lut = read_dem_binary(ranpix, self.nlines, self.npixels)  # [line, pixel] → longitude
        self.lat_lut = read_dem_binary(azpix, self.nlines, self.npixels)   # [line, pixel] → latitude
        # Create valid mask: both lat and lon must be finite
        self._valid_mask = np.isfinite(self.lat_lut) & np.isfinite(self.lon_lut)

    @property
    def valid_mask(self) -> np.ndarray:
        """
        Return the read-only valid mask of finite LUT points.

        Args:
            None.

        Returns:
            mask: Boolean valid-mask array.
        """
        return self._valid_mask

    def radar_to_geo(self, line: int, pixel: int) -> tuple[float, float]:
        """
        Convert radar coordinates to geographic coordinates.

        Args:
            line: Radar line index.
            pixel: Radar pixel index.

        Returns:
            lat_lon: Tuple (lat, lon) in degrees.
        """
        if not (0 <= line < self.nlines and 0 <= pixel < self.npixels):
            raise IndexError("Radar coordinates out of bounds.")
        lat = self.lat_lut[line, pixel]
        lon = self.lon_lut[line, pixel]
        if not (np.isfinite(lat) and np.isfinite(lon)):
            raise ValueError(f"Invalid geo coord at ({line}, {pixel})")
        return float(lat), float(lon)

    def geo_to_radar(self, lat: float, lon: float, k: int = 1, max_dist_deg: float = 0.1) -> tuple[int, int]:
        """
        Convert geographic coordinates to the nearest radar coordinate.

        Args:
            lat, lon: Input geographic coordinates (degrees)
            k: Number of neighbors to consider (default 1)
            max_dist_deg: Maximum allowed distance in degrees (e.g., 0.1° ≈ 11 km)

        Returns:
            line_pixel: Tuple (line, pixel) indices.

        Raises:
            ValueError if no valid point within max_dist_deg
        """
        dlat = self.lat_lut - lat
        dlon = self.lon_lut - lon
        dist2 = dlat**2 + dlon**2
        dist2[~self.valid_mask] = np.inf
        idx = np.argmin(dist2)
        line, pixel = np.unravel_index(idx, dist2.shape)
        if dist2[line, pixel] >= max_dist_deg ** 2:
            raise ValueError(f"No valid pixel within {max_dist_deg} degrees")
        return int(line), int(pixel)


##########################################################################
# Geocoding Routines
##########################################################################


def run_geocode_forward(dem_radar_filename: str,
                        resfile: str,
                        rlooks: int = 1,
                        alooks: int = 1,
                        output_lat: str = 'lat.rdr',
                        output_lon: str = 'lon.rdr',
                        log_file: str = 'run_geocode.log') -> None:
    """
    Generate forward geocoding lookup tables from radar to geographic coordinates.

    Args:
        dem_radar_filename: Input DEM file in radar coordinates
        resfile: Doris .res file containing orbit and geometry parameters
        rlooks: Range multilook factor
        alooks: Azimuth multilook factor
        output_lat: Output latitude file
        output_lon: Output longitude file
        log_file: Log file name

    Returns:
        result: None.
    """
    _print("Generate look-up table\n")

    # Set up logging
    set_log_file(log_file)

    # Create Orb and ImageGeometry from .res file
    # This currently uses a direct parser from the .res file.
    orb, image_geom = prepare_orbit_imagegeometry(resfile)

    nlines = image_geom.num_lines
    npixels = image_geom.num_pixels

    # DEM geometry placeholder (replace with DEM metadata when needed).

    # Create geocode processor
    processor = GeocodingProcessor(log_file=log_file)

    # Read DEM
    dem_radar = read_dem_binary(dem_radar_filename, nlines // alooks, npixels // rlooks)

    # Define product info
    product_info = ProductInfo(
        line_start=1,
        line_end=nlines,
        pixel_start=1,
        pixel_end=npixels,
        multilook_L=alooks,
        multilook_P=rlooks
    )

    # Define geocoding parameters
    geocode_input = ForwardGeocodeInput(
        dem_file=dem_radar_filename,
        output_phi=output_lat,
        output_lambda=output_lon,
        dem_format="real4"
    )

    # Run geocoding
    try:
        lat_grid, lon_grid = processor.create_lut_forwardgeocode(
            dem_radar=dem_radar,
            orbit=orb,
            image_geom=image_geom,
            product_info=product_info,
            geocode_input=geocode_input,
            overwrite=True
        )

        # Print statistics
        _print("Geocoding Results:")
        _print(f"- Output grid shape: {lat_grid.shape}")
        _print(f"- Latitude range: [{np.nanmin(lat_grid):.6f}, {np.nanmax(lat_grid):.6f}] degrees")
        _print(f"- Longitude range: [{np.nanmin(lon_grid):.6f}, {np.nanmax(lon_grid):.6f}] degrees")
        _print(f"- Valid points: {np.sum(~np.isnan(lat_grid))} / {lat_grid.size}")
    except Exception as e:
        print(f"Error during geocoding: {e}")
        import traceback
        traceback.print_exc()


# ------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------


def read_dem_binary(filename: str,
                    lines: int,
                    pixels: int,
                    dtype: str = 'float32') -> np.ndarray:
    """
    Read a binary DEM file and reshape it into a 2D array.

    Args:
        filename: Input file path
        lines: Number of lines
        pixels: Number of pixels
        dtype: Data type(default: float32)

    Returns:
        dem_array: DEM array with shape [lines, pixels].
    """
    data = np.fromfile(filename, dtype=dtype)
    expected_size = lines * pixels

    if len(data) != expected_size:
        raise ValueError(f"File size mismatch: expected {expected_size}, got {len(data)}")

    return data.reshape(lines, pixels)


def prepare_orbit_imagegeometry(resfile):
    """
    Build Orbit and ImageGeometry objects from a Doris .res file.

    Args:
        resfile: Path to Doris .res file

    Returns:
        orbit_image_geom: Tuple (orbit, image_geom).
    """
    parameters = DorisResParser.parse_res_file(resfile)
    orbit_data = parameters['orbit_data']

    # 1. Initialize orbit interpolator from orbit data vectors.
    orbit = Orbit(interp_method=5)  # Use 5th degree polynomial
    # Extract vectors from orbit_data list.
    time_vec = [record[0] for record in orbit_data]
    x_vec = [record[1] for record in orbit_data]
    y_vec = [record[2] for record in orbit_data]
    z_vec = [record[3] for record in orbit_data]

    # Check whether velocity data exists.
    has_velocity = len(orbit_data[0]) > 4
    if has_velocity:
        xv_vec = [record[4] for record in orbit_data]
        yv_vec = [record[5] for record in orbit_data]
        zv_vec = [record[6] for record in orbit_data]
        orbit.set_data(time_vec, x_vec, y_vec, z_vec, xv_vec, yv_vec, zv_vec)
    else:
        orbit.set_data(time_vec, x_vec, y_vec, z_vec)

    # 2. Build image geometry from .res file.
    # 2.1 Time parameters.
    first_dt = parameters['first_pixel_datetime']
    last_dt = parameters['last_pixel_datetime']
    day0 = first_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    # day_start1 = first_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    # day_start2 = last_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    first_line_time = (first_dt - day0).total_seconds()
    last_line_time = (last_dt - day0).total_seconds()
    # 2.2 PRF and line_time_interval.
    prf = parameters.get('prf_computed', parameters.get('prf', None))
    if prf is None or prf <= 0:
        raise ValueError("Invalid PRF value")
    line_time_interval = 1.0 / prf

    # 2.3 Range sampling rate and pixel_time_interval.
    range_sampling_rate_mhz = parameters.get('range_sampling_rate', 0.0)
    if range_sampling_rate_mhz <= 0:
        raise ValueError("Invalid range sampling rate")
    pixel_time_interval = 1.0 / (range_sampling_rate_mhz * 1e6)  # MHz -> Hz

    # 2.4 Image dimensions.
    num_lines = parameters.get('naz_original', 1)
    num_pixels = parameters.get('nr_original', 1)

    # 2.5 Range time values.
    near_range_time_ms = parameters.get('range_time_to_first_pixel', 0.0)
    near_range_time = near_range_time_ms / 1000.0  # ms → s

    first_pixel = parameters.get('first_pixel', 1) - 1
    if first_pixel > 0:
        # Adjust near_range_time to account for cropped pixels
        range_sampling_rate = parameters.get('range_sampling_rate', 240.0) * 1e6
        time_correction = first_pixel / range_sampling_rate
        near_range_time -= time_correction
        _print(f"Adjusted near_range_time for first_pixel={first_pixel}: {near_range_time*1000:.6f}ms")

    far_range_time = near_range_time + (num_pixels - 1) * pixel_time_interval

    # 2.6 Wavelength.
    wavelength = parameters.get('radar_wavelength', None)

    # 2.7 Look side.
    look_side = parameters.get('antenna_side', None)

    # 2.8 Incidence angle.
    incidence_angle_deg = parameters.get('incidence_angle', None)

    # 2.9 Scene center latitude/longitude.
    scene_center_lat = parameters.get('scene_center_lat', None)
    scene_center_lon = parameters.get('scene_center_lon', None)

    # 2.10 Scene corner latitude/longitude.
    scene_corner_lat = parameters.get('scene_corner_lat', [])
    scene_corner_lon = parameters.get('scene_corner_lon', [])

    # 2.11 Ground sampling spacing.
    azimuth_pixel_spacing = parameters.get('azimuth_pixel_spacing', None)
    range_pixel_spacing = parameters.get('range_pixel_spacing', None)

    # Final: construct ImageGeometry.
    image_geom = ImageGeometry(
        incidence_angle=incidence_angle_deg,
        first_line_time=first_line_time,
        last_line_time=last_line_time,
        near_range_time=near_range_time,
        far_range_time=far_range_time,
        line_time_interval=line_time_interval,
        pixel_time_interval=pixel_time_interval,
        num_lines=num_lines,
        num_pixels=num_pixels,
        prf=prf,
        wavelength=wavelength,
        antenna_side=look_side,
        fdp=[0.0],  # zero doppler
        scene_center_lat=scene_center_lat,
        scene_center_lon=scene_center_lon,
        azimuth_pixel_spacing=azimuth_pixel_spacing,
        range_pixel_spacing=range_pixel_spacing,
        scene_corner_lat=scene_corner_lat,
        scene_corner_lon=scene_corner_lon
    )
    return orbit, image_geom


def prepare_dem_geometry(log_out: str) -> 'DEMGeometry':
    """
    Prepare DEM geometry from interpolation/cropping logs (EQA only).

    Args:
        log_out: Path to the DEM processing log file.

    Returns:
        dem_geom: Parsed DEMGeometry object.
    """
    with open(log_out, 'r') as f:
        dem_logout = f.read()
    # --- 1. Extract "DEM output total lines/pixels" ---
    pattern = r"Output file cropped DEM:\s+demcrop\.raw.*?Number of lines \(multilooked\):\s+(\d+).*?Number of pixels \(multilooked\):\s+(\d+)"
    match = re.search(pattern, dem_logout, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("Failed to find 'demcrop.raw' size in log.")
    nrows = int(match.group(1))
    ncols = int(match.group(2))
    # --- 2. Extract "DEM extend w/e/s/n" ---
    extend_match = re.search(
        r"DEM extend w/e/s/n\s*:\s*([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+)",
        dem_logout
    )
    if not extend_match:
        raise ValueError("Could not find 'DEM extend w/e/s/n' in log file.")
    lon_west = float(extend_match.group(1))
    lon_east = float(extend_match.group(2))
    lat_south = float(extend_match.group(3))
    lat_north = float(extend_match.group(4))

    # --- 3. Calculate corner and posting ---
    # Upper-left = Northwest = (max_lat, min_lon)
    corner_lat = lat_north
    corner_lon = lon_west

    # Post: Direction info
    post_lat = (lat_south - lat_north) / (nrows - 1) if nrows > 1 else None
    post_lon = (lon_east - lon_west) / (ncols - 1) if ncols > 1 else None

    # --- 4. Extract NODATA value (optional) ---
    nodata_match = re.search(r"CRD_IN_NODATA\s*([-\d.]+)", dem_logout)
    nodata_value = float(nodata_match.group(1)) if nodata_match else -32768.0

    # --- 5. Build DEMGeometry ---
    dem_geom = DEMGeometry(
        projection='EQA',
        nrows=nrows,
        ncols=ncols,
        corner_lat=corner_lat,
        corner_lon=corner_lon,
        post_lat=post_lat,
        post_lon=post_lon,
        data_format='REAL4',
        nodata_value=nodata_value
    )
    return dem_geom
