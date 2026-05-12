import math

ALLOWED_RADIUS_METERS = 30  # metres — adjust as needed


def _trunc1(val: float) -> float:
    """Truncate a coordinate to 1 decimal place for coarse-grid checking.
    Example: 18.676777 → 18.6
    """
    return round(val, 1)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two GPS coordinates (Haversine formula)."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def is_within_radius(student_lat: float, student_lon: float,
                     classroom_lat: float, classroom_lon: float,
                     radius: float = ALLOWED_RADIUS_METERS) -> tuple[bool, float]:
    """Return (within_radius, distance_metres).
    Coordinates are truncated to 1 decimal place before comparison
    so 18.676777 becomes 18.6 for checking.
    """
    # Truncate to 1 decimal for coarse matching
    s_lat = _trunc1(student_lat)
    s_lon = _trunc1(student_lon)
    c_lat = _trunc1(classroom_lat)
    c_lon = _trunc1(classroom_lon)

    dist = calculate_distance(s_lat, s_lon, c_lat, c_lon)
    return dist <= radius, round(dist, 2)
