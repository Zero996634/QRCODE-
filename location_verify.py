import math

ALLOWED_RADIUS_METERS = 30  # metres — adjust as needed


def calculate_distance(lat1: int, lon1: int, lat2: int, lon2: int) -> float:
    """Return distance in metres between two GPS coordinates (Haversine formula)."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def is_within_radius(student_lat: int, student_lon: int,
                     classroom_lat: int, classroom_lon: int,
                     radius: int = ALLOWED_RADIUS_METERS) -> tuple[bool, int]:
    """Return (within_radius, distance_metres)."""
    dist = calculate_distance(student_lat, student_lon, classroom_lat, classroom_lon)
    return dist <= radius, round(dist, 2)
