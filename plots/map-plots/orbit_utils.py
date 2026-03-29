from datetime import datetime

import numpy as np
from numpy.typing import NDArray
from pymap3d.ecef import eci2geodetic
from scipy.spatial.transform import Rotation as R


def get_orbitecis(
    incl, raan, altitude, n, begin_time=0, Earth_R=6371, portion=1.0, retrograde=False
):
    """Generates a circular orbit based on given parameters

    Params:
        incl: Inclination in Degrees
        raan: Right Ascension to Ascending Node in Degrees
        altitude: Altitude in km
        n: amount of points needed for a full revolution
        begin_time: time in which to begin
        portion: ratio of the portion of points to be created

    Returns:
        A tuple
        (
            np array of r_eci points in km,
            np array of v_eci in km/s,
            delta seconds since beginning)
    """

    # Calculating r_eci
    if retrograde:
        sign = 1
    else:
        sign = -1
    points = []
    for i in range(int(n * portion)):
        points.append(
            [np.sin(sign * 2 * np.pi * (i / n)), np.cos(sign * 2 * np.pi * (i / n)), 0]
        )
    points = np.array(points) * (altitude + Earth_R)  # Plus height in km

    m_raan = R.from_rotvec(
        np.array([0, 0, 1]) * raan, degrees=True
    ).as_matrix()  # Rotation along the north-pole axis
    m_incl = R.from_rotvec(
        np.array([1, 0, 0]) * incl, degrees=True
    ).as_matrix()  # Rotation along the axis towards the ascending node

    raan_vec = np.matmul(m_raan, np.array([1, 0, 0]))
    incl_vec = np.matmul(m_incl, np.array([0, 1, 0]))
    incl_vec = np.matmul(m_raan, incl_vec)
    normal = np.cross(raan_vec, incl_vec)
    basechange_m = np.array([raan_vec, incl_vec, normal])

    r_ecis = np.matmul(basechange_m.T, points.T).T

    # Calculating Time periods
    mu = 398600.4418  # unit: (km)^3 / s^2
    period_s = ((2 * np.pi) / np.sqrt(mu)) * np.sqrt(
        altitude + Earth_R
    ) ** 3  # Period of one revolution
    delta_array = np.arange(0, period_s, period_s / n)
    time_array = [datetime.fromtimestamp(dt + begin_time) for dt in delta_array]

    # Calculating v_eci in km/s
    velocity = (2 * np.pi * (altitude + Earth_R)) / period_s
    v_ecis = []
    for r_eci in r_ecis:
        v_eci_ = np.cross(-r_eci, normal)
        v_eci_ = v_eci_ / np.linalg.norm(v_eci_)
        v_eci_ *= velocity
        v_ecis.append(v_eci_)
    v_ecis = np.array(v_ecis)

    return r_ecis, v_ecis, time_array


def slant_distance(e, h, R=6371):
    """
    Computes the slant distance based on elevation and altitude.

    e: Elevation in degrees
    h: Altitude in km

    Returns

    d: slant distance in km
    """
    B = -2 * R * np.cos(np.radians(90 + e))
    C = -2 * R * h - h**2
    # Solving a geometric equation where only one is real
    d = (-B + np.sqrt(B**2 - 4 * C)) / 2.0
    return d


def get_coords(
    incl, raan, altitude, n, begin_time=0, portion=1.0
) -> NDArray[np.float64]:
    """Generates ground track of a  circular orbit based on given parameters

    Params:
        incl: Inclination in Degrees
        raan: Right Ascension to Ascending Node in Degrees
        altitude: Altitude in km
        n: amount of points to be generated
        begin_time: time in which to begin

    Returns:
        array of lat long tuples
    """
    ps, vs, ts = get_orbitecis(incl, raan, altitude, n, begin_time, portion=portion)

    coords = []
    for point, fwd, time in zip(ps, vs, ts):
        lat, long, altitude = eci2geodetic(*(point * 1000), time)
        coords.append((lat[0], long[0]))
    return np.array(coords)
