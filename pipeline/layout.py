"""Store layout utilities for zone lookup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import json
from pathlib import Path

Point = Tuple[float, float]


@dataclass(frozen=True)
class Zone:
    zone_id: str
    label: str
    zone_type: str
    polygon: List[Point]


@dataclass(frozen=True)
class Layout:
    store_id: str
    image_width: int
    image_height: int
    zones: List[Zone]
    zones_by_id: Dict[str, Zone]

    def zone_for_point(self, point: Point) -> Optional[Zone]:
        for zone in self.zones:
            if _point_in_polygon(point, zone.polygon):
                return zone
        return None


def load_layout(path: str | Path) -> Layout:
    layout_path = Path(path)
    data = json.loads(layout_path.read_text(encoding="utf-8"))
    zones = [
        Zone(
            zone_id=zone["zone_id"],
            label=zone.get("label", zone["zone_id"]),
            zone_type=zone.get("type", "unknown"),
            polygon=[tuple(point) for point in zone["polygon"]],
        )
        for zone in data["zones"]
    ]
    zones_by_id = {zone.zone_id: zone for zone in zones}
    image = data.get("image", {})
    return Layout(
        store_id=data.get("store_id", "UNKNOWN"),
        image_width=int(image.get("width", 0)),
        image_height=int(image.get("height", 0)),
        zones=zones,
        zones_by_id=zones_by_id,
    )


def _point_in_polygon(point: Point, polygon: Iterable[Point]) -> bool:
    x, y = point
    inside = False
    points = list(polygon)
    if not points:
        return False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        intersect = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi
        if intersect:
            inside = not inside
        j = i
    return inside
