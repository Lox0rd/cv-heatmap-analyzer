"""Draw stored polygon zones on a BGR video frame."""

import cv2
import numpy as np

from src.zones.zone_manager import Zone


def draw_zones(frame: np.ndarray, zones: list[Zone]) -> np.ndarray:
    result = frame.copy()
    for number, zone in enumerate(zones, start=1):
        points = np.asarray(zone.points, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(result, [points], True, (255, 210, 50), 3)
        x, y = zone.points[0]
        center = (max(14, x), max(14, y))
        cv2.circle(result, center, 13, (10, 65, 100), -1)
        cv2.putText(
            result, str(number), (center[0] - 5, center[1] + 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA,
        )
    return result
