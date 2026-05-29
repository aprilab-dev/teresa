#!/usr/bin/env python3
import numpy as np
from datetime import datetime
from typing import  Tuple
from scipy.linalg import cho_factor, cho_solve
from dataclasses import dataclass

# Constants
SOL = 299792458.0  # Speed of light [m/s]
EPS = 1e-15
ORB_SPLINE = -1
ORB_DEFAULT = 0

_log_file = None  # Global log file variable


def _print(*args, **kwargs):
    """Define a custom print function that outputs to console and log file."""
    global _log_file
    if _log_file:
        try:
            with open(_log_file, 'a', encoding='utf-8') as f:
                # Convert arguments to string and join them with spaces
                message = ' '.join(str(arg) for arg in args)
                # Add timestamp to the message
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")


def set_log_file(log_file_path: str, mode='w'):
    """Set the path for the log file."""
    global _log_file
    _log_file = log_file_path
    # Clear the log file or create a new one
    try:
        with open(_log_file, mode, encoding='utf-8') as f:
            f.write(f"Processing Log - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n")
    except Exception as e:
        print(f"Error creating log file: {e}")


@dataclass
class Point3D:
    """3D point or vector representation"""
    x: float
    y: float
    z: float

    def __add__(self, other):
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Point3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def norm(self):
        """Euclidean norm"""
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)

    def to_array(self):
        """Convert to numpy array"""
        return np.array([self.x, self.y, self.z])

    @classmethod
    def from_array(cls, arr):
        """Create from numpy array"""
        return cls(arr[0], arr[1], arr[2])


@dataclass
class Ellipsoid:
    """Reference ellipsoid parameters"""
    a: float = 6378137.0  # Semi-major axis [m] - WGS84
    b: float = 6356752.314245  # Semi-minor axis [m] - WGS84
    name: str = "WGS84"  # Ellipsoid name

    @property
    def e2(self):
        """First eccentricity squared"""
        return (self.a**2 - self.b**2) / self.a**2

    @property
    def e2b(self):
        """Second eccentricity squared"""
        return (self.a**2 - self.b**2) / self.b**2

    def show_data(self):
        """Display ellipsoid parameters"""
        _print(f"ELLIPSOID: Ellipsoid used (orbit, output): {self.name}.")
        _print(f"ELLIPSOID: a   = {self.a:.13f}")
        _print(f"ELLIPSOID: b   = {self.b:.13f}")
        _print(f"ELLIPSOID: e2  = {self.e2:.18f}")
        _print(f"ELLIPSOID: e2' = {self.e2b:.18f}")

    def lla2xyz(self, lat: float, lon: float, height: float = 0.0) -> Point3D:
        """
        Convert geodetic coordinates (lat, lon, height) to ECEF XYZ

        Args:
            lat: Latitude [degrees]
            lon: Longitude [degrees]
            height: Height above ellipsoid [meters]

        Returns:
            Point3D in ECEF coordinates [meters]
        """
        lat_rad = np.radians(lat)
        lon_rad = np.radians(lon)

        # Radius of curvature in prime vertical
        N = self.a / np.sqrt(1 - self.e2 * np.sin(lat_rad)**2)

        x = (N + height) * np.cos(lat_rad) * np.cos(lon_rad)
        y = (N + height) * np.cos(lat_rad) * np.sin(lon_rad)
        z = (N * (1 - self.e2) + height) * np.sin(lat_rad)

        return Point3D(x, y, z)

    def xyz2lla(self, pos: Point3D) -> Tuple[float, float, float]:
        """
        Convert ECEF XYZ to geodetic coordinates (lat, lon, height)
        Using Bowring's method as implemented in the C++ reference code

        Args:
            pos: Point3D in ECEF coordinates [meters]

        Returns:
            Tuple of (latitude [deg], longitude [deg], height [m])
        """
        # Longitude
        lon = np.arctan2(pos.y, pos.x)

        # Iterative solution for latitude and height
        p = np.sqrt(pos.x**2 + pos.y**2)
        nu = np.arctan2(pos.z * self.a, p * self.b)
        sin3 = np.sin(nu)**3
        cos3 = np.cos(nu)**3
        lat = np.arctan2(
            pos.z + self.e2b * self.b * sin3,
            p - self.e2 * self.a * cos3
        )

        # Calculate height
        N = self.a / np.sqrt(1 - self.e2 * np.sin(lat)**2)
        height = p / np.cos(lat) - N

        return np.degrees(lat), np.degrees(lon), height

    def xyz2ell(self, pos: Point3D) -> Tuple[float, float]:
        """
        Convert ECEF XYZ to geodetic coordinates (lat, lon) without height
        Using Bowring's method as implemented in the C++ reference code

        Args:
            pos: Point3D in ECEF coordinates [meters]

        Returns:
            Tuple of (latitude [rad], longitude [rad])
        """
        # Longitude
        lon = np.arctan2(pos.y, pos.x)

        # Bowring's method for latitude
        p = np.sqrt(pos.x**2 + pos.y**2)
        nu = np.atan2(pos.z * self.a, p * self.b)
        sin3 = np.sin(nu)**3
        cos3 = np.cos(nu)**3

        # Calculate latitude
        lat = np.arctan2(
            pos.z + self.e2b * self.b * sin3,
            p - self.e2 * self.a * cos3
        )

        return lat, lon


class Orbit:
    """
    Orbit interpolation class

    Handles satellite orbit state vector interpolation using either
    cubic splines or polynomial fitting. Now supports direct initialization
    from in-memory orbit vectors.

    Attributes:
        time: Time stamps of orbit data points [seconds]
        data_x, data_y, data_z: Position coordinates [meters]
        data_xv, data_yv, data_zv: Velocity components [m/s] (optional)
        interp_method: Interpolation method (ORB_SPLINE or polynomial degree)
        coef_x, coef_y, coef_z: Interpolation coefficients
        numberofpoints: Number of orbit data points
    """

    def __init__(self, interp_method=ORB_DEFAULT):
        """
        Initialize orbit object

        Args:
            interp_method: Interpolation method
                          -1 for cubic spline
                          0 for automatic selection
                          >0 for polynomial degree
        """
        self.time = None
        self.data_x = None
        self.data_y = None
        self.data_z = None
        self.data_xv = None
        self.data_yv = None
        self.data_zv = None
        self.interp_method = interp_method
        self.coef_x = None
        self.coef_y = None
        self.coef_z = None
        self.numberofpoints = 0
        self.klo = 0
        self.khi = 1

    def set_data(self, time_data, x_data, y_data, z_data,
                 xv_data=None, yv_data=None, zv_data=None):
        """
        Initialize orbit from in-memory vectors

        Args:
            time_data: List/array of time values [seconds]
            x_data, y_data, z_data: Position vectors [meters]
            xv_data, yv_data, zv_data: Velocity vectors [m/s] (optional)
        """
        # Convert to numpy arrays
        self.time = np.array(time_data, dtype=float)
        self.data_x = np.array(x_data, dtype=float)
        self.data_y = np.array(y_data, dtype=float)
        self.data_z = np.array(z_data, dtype=float)
        self.numberofpoints = len(self.time)

        # Store velocity data if provided
        if xv_data is not None and yv_data is not None and zv_data is not None:
            self.data_xv = np.array(xv_data, dtype=float)
            self.data_yv = np.array(yv_data, dtype=float)
            self.data_zv = np.array(zv_data, dtype=float)
        else:
            self.data_xv = None
            self.data_yv = None
            self.data_zv = None

        # Validate data
        if self.numberofpoints < 4:
            raise ValueError(f"Insufficient orbit points: {self.numberofpoints} (min 4 required)")

        # Check if time sorted
        dt = np.diff(self.time)
        if np.any(dt < EPS):
            raise ValueError("Orbit time axis: require distinct, time sorted data")

        # Set default interpolation method if not specified
        if self.interp_method == ORB_DEFAULT:
            self.interp_method = 5 if self.numberofpoints > 6 else self.numberofpoints - 2

            # Special handling for RADARSAT (large time intervals)
            if len(dt) > 0 and 479.9 < dt[0] < 481.1:
                _print(f"Warning: Assuming RADARSAT: using highest polyfit")
                self.interp_method = self.numberofpoints - 1

        _print(f"Using interpolation method: {self.interp_method}")

        # Compute interpolation coefficients
        self.compute_coefficients()
        _print(f"Orbit interpolation coefficients computed for {self.numberofpoints} points")

    def compute_coefficients(self):
        """
        Computes interpolation coefficients for either cubic spline or polynomial
        interpolation based on self.interp_method.
        """
        if self.interp_method == ORB_SPLINE:
            _print("Computing cubic spline interpolation coefficients")
            self.coef_x = self._spline_interpol(self.time, self.data_x)
            self.coef_y = self._spline_interpol(self.time, self.data_y)
            self.coef_z = self._spline_interpol(self.time, self.data_z)
        else:
            if self.interp_method < 0:
                raise ValueError("Polynomial degree cannot be negative")
            _print(f"Computing polynomial fit coefficients (degree {self.interp_method})")
            self.coef_x = self._polyfit(self.time, self.data_x, self.interp_method)
            self.coef_y = self._polyfit(self.time, self.data_y, self.interp_method)
            self.coef_z = self._polyfit(self.time, self.data_z, self.interp_method)

    def _spline_interpol(self, time, data):
        """
        Compute natural cubic spline coefficients

        Based on Numerical Recipes spline routine.
        Uses natural boundary conditions (second derivative = 0 at endpoints).

        Args:
            time: Time vector
            data: Data vector (x, y, or z coordinates)

        Returns:
            Second derivatives at data points
        """
        n = len(time)
        rhs = np.zeros(n - 1)
        pp = np.zeros(n)

        # Natural spline boundary condition at first point
        pp[0] = 0.0

        # Decomposition loop
        for i in range(1, n - 1):
            sig = (time[i] - time[i-1]) / (time[i+1] - time[i-1])
            p = sig * pp[i-1] + 2.0
            pp[i] = (sig - 1.0) / p

            rhs[i] = (data[i+1] - data[i]) / (time[i+1] - time[i]) - \
                     (data[i] - data[i-1]) / (time[i] - time[i-1])
            rhs[i] = (6.0 * rhs[i] / (time[i+1] - time[i-1]) - sig * rhs[i-1]) / p

        # Natural spline boundary condition at last point
        pp[n-1] = 0.0

        # Back substitution loop
        for i in range(n-2, -1, -1):
            pp[i] = pp[i] * pp[i+1] + rhs[i]

        return pp

    def _polyfit(self, time, y, degree):
        """
        Polynomial least squares fit

        Fits polynomial of specified degree to data points.
        Time axis is normalized for numerical stability.

        Args:
            time: Time vector
            y: Data vector (x, y, or z coordinates)
            degree: Degree of polynomial

        Returns:
            Polynomial coefficients [a0, a1, a2, ..., a_degree]
        """
        n_points = len(time)
        n_unk = degree + 1

        if n_points < n_unk:
            raise ValueError("Number of points smaller than parameters to solve")

        # Normalize time axis for numerical stability
        t_mid = time[n_points // 2]
        t = (time - t_mid) / 10.0

        # Build design matrix
        A = np.zeros((n_points, n_unk))
        for j in range(n_unk):
            A[:, j] = t ** j

        # Solve normal equations using Cholesky decomposition
        N = A.T @ A
        rhs = A.T @ y

        try:
            c, lower = cho_factor(N)
            coeff = cho_solve((c, lower), rhs)
        except np.linalg.LinAlgError:
            _print(f"Warning:Cholesky failed, using lstsq")
            coeff = np.linalg.lstsq(A, y, rcond=None)[0]

        # Check approximation quality
        y_hat = A @ coeff
        e_hat = y - y_hat
        max_error = np.max(np.abs(e_hat))

        if max_error > 0.02:
            _print(f"Warning:Max approximation error: {max_error:.6f} m")
        else:
            _print(f"Max approximation error: {max_error:.6f} m")

        return coeff

    def polyval1d(self, t, coeff, der=0):
        """
        Evaluate polynomial or its derivative at time t
        Args:
            t: Time value
            coeff: Polynomial coefficients [a0, a1, ..., aN]
            der: Derivative order (0 for value, 1 for first derivative, 2 for second derivative)

        Returns:
            Evaluated polynomial or its derivative at time t
        """
        degree = len(coeff) - 1

        if der == 0:
            # 位置
            result = coeff[degree]
            for i in range(degree-1, -1, -1):
                result = result * t + coeff[i]
            return result

        elif der == 1:
            # 一阶导数（速度）
            if degree < 1:
                return 0.0
            result = coeff[degree] * degree
            for i in range(degree-1, 0, -1):
                result = result * t + coeff[i] * i
            return result

        elif der == 2:
            # 二阶导数（加速度）
            if degree < 2:
                return 0.0
            result = coeff[degree] * degree * (degree-1)
            for i in range(degree-1, 1, -1):
                result = result * t + coeff[i] * i * (i-1)
            return result

        else:
            raise ValueError(f"Unsupported derivative order: {der}")

    def _get_interval(self, t):
        """
        Find interval [klo, khi] containing time t
        Uses cached values when possible for efficiency.

        Args:
            t: Time value to interpolate
        """
        # Check if last interval still applies
        if self.time[self.klo] <= t <= self.time[self.khi]:
            return

        # Binary search for correct interval
        self.klo = 0
        self.khi = self.numberofpoints - 1

        while self.khi - self.klo > 1:
            k = (self.khi + self.klo) >> 1
            if self.time[k] > t:
                self.khi = k
            else:
                self.klo = k

    def get_xyz(self, t: float) -> Point3D:
        """
        Get interpolated position at time t

        Args:
            t: Time value [seconds]

        Returns:
            Point3D with interpolated (x, y, z) position [meters]
        """
        if t < self.time[0] or t > self.time[-1]:
            _print(f"Warning:Interpolation at t={t} outside time axis "
                   f"[{self.time[0]}, {self.time[-1]}]")

        if self.interp_method == ORB_SPLINE:
            # Cubic spline interpolation
            self._get_interval(t)
            h = self.time[self.khi] - self.time[self.klo]
            a = (self.time[self.khi] - t) / h
            b = 1.0 - a

            x = (a * self.data_x[self.klo] + b * self.data_x[self.khi] +
                 ((a**3 - a) * self.coef_x[self.klo] +
                 (b**3 - b) * self.coef_x[self.khi]) * h**2 / 6.0)

            y = (a * self.data_y[self.klo] + b * self.data_y[self.khi] +
                 ((a**3 - a) * self.coef_y[self.klo] +
                 (b**3 - b) * self.coef_y[self.khi]) * h**2 / 6.0)

            z = (a * self.data_z[self.klo] + b * self.data_z[self.khi] +
                 ((a**3 - a) * self.coef_z[self.klo] +
                 (b**3 - b) * self.coef_z[self.khi]) * h**2 / 6.0)
        else:
            # Polynomial interpolation - C++ style implementation
            t_norm = (t - self.time[self.numberofpoints // 2]) / 10.0
            x = self.polyval1d(t_norm, self.coef_x, 0)
            y = self.polyval1d(t_norm, self.coef_y, 0)
            z = self.polyval1d(t_norm, self.coef_z, 0)

        return Point3D(x, y, z)

    def get_xyz_dot(self, t: float) -> Point3D:
        """
        Get interpolated velocity at time t

        Args:
            t: Time value [seconds]

        Returns:
            Point3D with interpolated velocity (vx, vy, vz) [m/s]
        """
        if t < self.time[0] or t > self.time[-1]:
            _print(f"Warning:Interpolation at t={t} outside time axis "
                   f"[{self.time[0]}, {self.time[-1]}]")

        if self.interp_method == ORB_SPLINE:
            # First derivative of cubic spline
            self._get_interval(t)
            h = self.time[self.khi] - self.time[self.klo]
            a = (self.time[self.khi] - t) / h
            b = 1.0 - a

            vx = ((self.data_x[self.khi] - self.data_x[self.klo]) / h +
                  h * ((1 - 3*a**2) * self.coef_x[self.klo] +
                       (3*b**2 - 1) * self.coef_x[self.khi]) / 6.0)

            vy = ((self.data_y[self.khi] - self.data_y[self.klo]) / h +
                  h * ((1 - 3*a**2) * self.coef_y[self.klo] +
                       (3*b**2 - 1) * self.coef_y[self.khi]) / 6.0)

            vz = ((self.data_z[self.khi] - self.data_z[self.klo]) / h +
                  h * ((1 - 3*a**2) * self.coef_z[self.klo] +
                       (3*b**2 - 1) * self.coef_z[self.khi]) / 6.0)
        else:
            # Polynomial derivative
            t_norm = (t - self.time[self.numberofpoints // 2]) / 10.0
            vx = self.polyval1d(t_norm, self.coef_x, 1) / 10.0  # 除以10.0归一化
            vy = self.polyval1d(t_norm, self.coef_y, 1) / 10.0
            vz = self.polyval1d(t_norm, self.coef_z, 1) / 10.0

        return Point3D(vx, vy, vz)

    def get_xyz_ddot(self, t: float) -> Point3D:
        """
        Get interpolated acceleration at time t

        Args:
            t: Time value [seconds]

        Returns:
            Point3D with interpolated acceleration (ax, ay, az) [m/s^2]
        """
        if t < self.time[0] or t > self.time[-1]:
            _print(f"Warning:Interpolation at t={t} outside time axis "
                   f"[{self.time[0]}, {self.time[-1]}]")

        if self.interp_method == ORB_SPLINE:
            # Second derivative of cubic spline
            self._get_interval(t)
            h = self.time[self.khi] - self.time[self.klo]
            a = (self.time[self.khi] - t) / h
            b = 1.0 - a

            ax = a * self.coef_x[self.klo] + b * self.coef_x[self.khi]
            ay = a * self.coef_y[self.klo] + b * self.coef_y[self.khi]
            az = a * self.coef_z[self.klo] + b * self.coef_z[self.khi]
        else:
            # Second derivative of polynomial
            t_norm = (t - self.time[self.numberofpoints // 2]) / 10.0
            ax = self.polyval1d(t_norm, self.coef_x, 2) / 100.0  # 除以100.0归一化
            ay = self.polyval1d(t_norm, self.coef_y, 2) / 100.0
            az = self.polyval1d(t_norm, self.coef_z, 2) / 100.0

        return Point3D(ax, ay, az)

    def dump_orbit(self, filename: str, dt: float = 1.0):
        """
        Export interpolated orbit to file

        Args:
            filename: Output file path
            dt: Time step for output [seconds]
        """
        if self.numberofpoints == 0:
            _print("No orbit data available")
            return

        n_output = int((self.time[-1] - self.time[0]) / dt) + 1

        with open(filename, 'w') as f:
            f.write("# time [s]  x [m]  y [m]  z [m]  vx [m/s]  vy [m/s]  vz [m/s]  "
                    "ax [m/s^2]  ay [m/s^2]  az [m/s^2]\n")

            for i in range(n_output):
                t = self.time[0] + i * dt
                pos = self.get_xyz(t)
                vel = self.get_xyz_dot(t)
                acc = self.get_xyz_ddot(t)

                f.write(f"{t:15.3f} {pos.x:18.3f} {pos.y:18.3f} {pos.z:18.3f} "
                        f"{vel.x:12.6f} {vel.y:12.6f} {vel.z:12.6f} "
                        f"{acc.x:12.9f} {acc.y:12.9f} {acc.z:12.9f}\n")

        _print(f"Orbit dumped to: {filename}")

    def show_data(self):
        """Print orbit data summary"""
        _print(f"\nOrbit Data Summary:")
        _print(f"Number of points: {self.numberofpoints}")
        _print(f"Orbit Time range: [{self.time[0]:.3f}, {self.time[-1]:.3f}] s")
        _print(f"Interpolation method: {self.interp_method}")
        _print(f"Position range:")
        _print(f"  X: [{np.min(self.data_x):.3f}, {np.max(self.data_x):.3f}] m")
        _print(f"  Y: [{np.min(self.data_y):.3f}, {np.max(self.data_y):.3f}] m")
        _print(f"  Z: [{np.min(self.data_z):.3f}, {np.max(self.data_z):.3f}] m")


# Helper functions for coordinate transformations
def eq1_doppler(vel: Point3D, dsat_p: Point3D) -> float:
    """Doppler equation: v · (P - S) = 0"""
    return vel.x * dsat_p.x + vel.y * dsat_p.y + vel.z * dsat_p.z


def eq2_range(dsat_p: Point3D, range_time: float) -> float:
    """Range equation: |P - S|^2 - (c * t_range)^2 = 0"""
    return dsat_p.x**2 + dsat_p.y**2 + dsat_p.z**2 - (SOL * range_time)**2


def eq3_ellipsoid(pos: Point3D, ell_a: float, ell_b: float, height: float = 0.0) -> float:
    """
    Ellipsoid equation using original ellipsoid parameters (not elevated)
    Matches C++ reference implementation: x²/a² + y²/a² + z²/b² - 1 = 0
    """
    a_elev = ell_a + height
    b_elev = ell_b + height
    return pos.x**2 / a_elev**2 + pos.y**2 / a_elev**2 + pos.z**2 / b_elev**2 - 1.0


def solve33(equation_set, jacobian):
    """
    Solve 3x3 linear system using Cramer's rule for speed and stability
    Returns delta_pos array with solution
    """
    f1, f2, f3 = equation_set
    J00, J01, J02 = jacobian[0, 0], jacobian[0, 1], jacobian[0, 2]
    J10, J11, J12 = jacobian[1, 0], jacobian[1, 1], jacobian[1, 2]
    J20, J21, J22 = jacobian[2, 0], jacobian[2, 1], jacobian[2, 2]

    # Compute determinant
    det = (J00*(J11*J22 - J12*J21) -
           J01*(J10*J22 - J12*J20) +
           J02*(J10*J21 - J11*J20))

    if abs(det) < 1e-20:
        return None

    # Cramer's rule
    dx = ((-f1)*(J11*J22 - J12*J21) -
          J01*((-f2)*J22 - J12*(-f3)) +
          J02*((-f2)*J21 - J11*(-f3))) / det

    dy = (J00*((-f2)*J22 - J12*(-f3)) -
          (-f1)*(J10*J22 - J12*J20) +
          J02*(J10*(-f3) - (-f2)*J20)) / det

    dz = (J00*(J11*(-f3) - (-f2)*J21) -
          J01*(J10*(-f3) - (-f2)*J20) +
          (-f1)*(J10*J21 - J11*J20)) / det

    return np.array([dx, dy, dz])
