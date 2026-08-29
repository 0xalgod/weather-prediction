"""Coordinate-to-IANA-boundary and station identity verification helpers."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence


def point_in_ring(lon: float, lat: float, ring: Sequence[Sequence[float]]) -> bool:
    """Return whether a point is inside a GeoJSON linear ring using ray casting."""

    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[0], previous[1]
        x2, y2 = current[0], current[1]
        if (y1 > lat) != (y2 > lat):
            crossing = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lon < crossing:
                inside = not inside
        previous = current
    return inside


def point_in_polygon(lon: float, lat: float, polygon: Sequence[Sequence[Sequence[float]]]) -> bool:
    """Apply GeoJSON exterior-ring and hole semantics."""

    return bool(polygon and point_in_ring(lon, lat, polygon[0]) and not any(point_in_ring(lon, lat, hole) for hole in polygon[1:]))


def timezone_at_point(lon: float, lat: float, features: Iterable[Mapping[str, Any]]) -> str:
    """Resolve one point against timezone-boundary GeoJSON features."""

    matches = []
    for feature in features:
        geometry = feature["geometry"]
        polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        if any(point_in_polygon(lon, lat, polygon) for polygon in polygons):
            matches.append(feature["properties"]["tzid"])
    if len(matches) != 1:
        raise ValueError(f"expected one timezone boundary match, found {matches}")
    return matches[0]
