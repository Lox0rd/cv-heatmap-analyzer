"""Accumulate object activity inside polygon zones over video time."""

import json
from pathlib import Path

import cv2
import numpy as np

from src.zones.zone_manager import Zone


class ZoneStatistics:
    def __init__(self, zones: list[Zone], fps: float, source_key: str):
        self.zones = list(zones)
        self.fps = fps if fps > 0 else 30.0
        self.source_key = source_key
        self.frames_processed = 0
        self.total_observations = 0
        self._contours = {
            zone.name: np.asarray(zone.points, dtype=np.int32).reshape((-1, 1, 2))
            for zone in zones
        }
        self._counts = {zone.name: 0 for zone in zones}
        self._tracks = {zone.name: set() for zone in zones}
        self._timeline = {}

    def add_frame(self, frame_index: int, detections: list[dict]) -> None:
        second = max(0, int(frame_index / self.fps))
        bucket = self._timeline.setdefault(
            second,
            {"second": second, "total": 0, "zones": {name: 0 for name in self._counts}},
        )
        self.frames_processed += 1
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            foot = ((x1 + x2) / 2, y2)
            track_id = detection.get("track_id")
            track_key = (detection.get("label"), track_id)
            self.total_observations += 1
            bucket["total"] += 1
            for name, contour in self._contours.items():
                if cv2.pointPolygonTest(contour, foot, False) >= 0:
                    self._counts[name] += 1
                    bucket["zones"][name] += 1
                    if track_id is not None:
                        self._tracks[name].add(track_key)

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "source_key": self.source_key,
            "fps": self.fps,
            "frames_processed": self.frames_processed,
            "total_observations": self.total_observations,
            "zones": [
                {
                    "name": zone.name,
                    "observations": self._counts[zone.name],
                    "unique_objects": len(self._tracks[zone.name]),
                }
                for zone in self.zones
            ],
            "timeline": [self._timeline[second] for second in sorted(self._timeline)],
        }

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(path)
