#!/usr/bin/env python3
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Literal, Optional

@dataclass
class ImageGeometry:
    """SAR image geometry parameters"""
    scene_center_lat: float  # degrees
    scene_center_lon: float  # degrees
    incidence_angle: float  # degrees
    first_line_time: float  # Azimuth time of first line [s]
    last_line_time: float   # Azimuth time of last line [s]
    near_range_time: float  # Slant range time to near range [s]
    far_range_time: float   # Slant range time to far range [s]
    line_time_interval: float  # Time between lines [s]
    pixel_time_interval: float  # Time between pixels [s]
    num_lines: int  # Number of image lines
    num_pixels: int  # Number of image pixels
    prf: float  # prf
    wavelength: float  # Radar wavelength [m]
    antenna_side: str = 'right'  # 'left' or 'right'
    fdp: list = None
    range_pixel_spacing: Optional[float] = None  # Range pixel spacing [m]
    azimuth_pixel_spacing: Optional[float] = None  # Azimuth pixel spacing [m]
    scene_corner_lat: Optional[list[float, float, float, float]] = None
    scene_corner_lon: Optional[list[float, float, float, float]] = None

    def line2ta(self, line: float) -> float:
        """Convert line number to azimuth time [s]"""
        return self.first_line_time + (line - 1) * self.line_time_interval

    def pix2tr(self, pixel: float) -> float:
        """Convert pixel number to range time [s]"""
        return self.near_range_time + (pixel - 1) * self.pixel_time_interval


@dataclass
class DEMGeometry:
    """
    DEM geometry metadata in map projection (geographic or projected)

    Corresponds to DEM parameter fields in Doris/Gamma/ESA processing logs.
    Designed to replace the loose 'dem_par' dict.
    """
    # --- Projection type ---
    projection: Literal['EQA', 'UTM']  # Currently only support EQA (geographic)

    # --- Grid dimensions ---
    nrows: int      # Number of rows (latitude direction or north)
    ncols: int      # Number of columns (longitude direction or east)

    # --- Upper-left corner (in map units) ---
    corner_lat: float  # Latitude of upper-left corner (degrees, for EQA)
    corner_lon: float  # Longitude of upper-left corner (degrees, for EQA)
    # For UTM, you'd have corner_north, corner_east instead

    # --- Grid spacing (post) ---
    post_lat: float    # Latitude spacing (degrees), usually negative (N->S)
    post_lon: float    # Longitude spacing (degrees), usually positive (W->E)
    # For UTM: post_north, post_east (meters)

    # --- Data format and nodata ---
    data_format: Literal['REAL4', 'SHORT'] = 'REAL4'
    nodata_value: Optional[float] = None  # e.g., -32768

    # --- Optional: ellipsoid (if different from WGS84) ---
    ellipsoid_name: str = 'WGS84'
    ellipsoid_a: float = 6378137.0      # semi-major axis (m)
    ellipsoid_b: float = 6356752.314245  # semi-minor axis (m)

    @property
    def lat_grid(self) -> 'np.ndarray':
        """Generate 1D latitude array (from north to south)"""
        import numpy as np
        return self.corner_lat + np.arange(self.nrows) * self.post_lat

    @property
    def lon_grid(self) -> 'np.ndarray':
        """Generate 1D longitude array (from west to east)"""
        import numpy as np
        return self.corner_lon + np.arange(self.ncols) * self.post_lon


@dataclass
class ProductInfo:
    """Product information with windowing and multilook parameters"""
    line_start: int
    line_end: int
    pixel_start: int
    pixel_end: int
    multilook_L: int
    multilook_P: int
    formatflag: int = 1  # 1 for real4 format
