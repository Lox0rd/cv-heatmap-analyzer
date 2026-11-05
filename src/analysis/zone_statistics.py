"""Count people in frames and observed entries into polygon zones."""

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
        self.person_observations = 0
        self.untracked_person_observations = 0
        self.peak_people_in_frame = 0
        self._unique_people = set()
        self._contours = {
            zone.name: np.asarray(zone.points, dtype=np.int32).reshape((-1, 1, 2))
            for zone in zones
        }
        self._visitors = {zone.name: set() for zone in zones}
        self._entries = {zone.name: 0 for zone in zones}
        self._peak_in_zone = {zone.name: 0 for zone in zones}
        self._last_zones_by_track = {}
        self._timeline = {}

    def add_frame(self, frame_index: int, detections: list[dict]) -> int:
        """Return the number of people visible in this processed frame."""
        second = max(0, int(frame_index / self.fps))
        bucket = self._timeline.setdefault(
            second,
            {
                "second": second,
                "people_in_frame_peak": 0,
                "zone_people_peak": {name: 0 for name in self._contours},
                "zone_entries": {name: 0 for name in self._contours},
            },
        )
        self.frames_processed += 1

        people = []
        seen_tracks_in_frame = set()
        for detection in detections:
            if detection.get("label") != "person":
                continue
            track_id = detection.get("track_id")
            if track_id is not None:
                if track_id in seen_tracks_in_frame:
                    continue
                seen_tracks_in_frame.add(track_id)
            people.append(detection)

        count = len(people)
        self.person_observations += count
        self.peak_people_in_frame = max(self.peak_people_in_frame, count)
        bucket["people_in_frame_peak"] = max(bucket["people_in_frame_peak"], count)
        occupancy = {name: 0 for name in self._contours}

        for person in people:
            x1, _, x2, y2 = person["bbox"]
            foot = ((x1 + x2) / 2, y2)
            current_zones = {
                name
                for name, contour in self._contours.items()
                if cv2.pointPolygonTest(contour, foot, False) >= 0
            }
            track_id = person.get("track_id")
            for name in current_zones:
                occupancy[name] += 1
                if track_id is not None:
                    self._visitors[name].add(track_id)
            if track_id is None:
                self.untracked_person_observations += 1
                continue
            self._unique_people.add(track_id)
            previous_zones = self._last_zones_by_track.get(track_id)
            if previous_zones is not None:
                for name in current_zones - previous_zones:
                    self._entries[name] += 1
                    bucket["zone_entries"][name] += 1
            self._last_zones_by_track[track_id] = current_zones

        for name, value in occupancy.items():
            self._peak_in_zone[name] = max(self._peak_in_zone[name], value)
            bucket["zone_people_peak"][name] = max(
                bucket["zone_people_peak"][name], value
            )
        return count

    def to_dict(self) -> dict:
        return {
            "version": 2,
            "source_key": self.source_key,
            "fps": self.fps,
            "frames_processed": self.frames_processed,
            "person_observations": self.person_observations,
            "untracked_person_observations": self.untracked_person_observations,
            "unique_people": len(self._unique_people),
            "peak_people_in_frame": self.peak_people_in_frame,
            "total_zone_entries": sum(self._entries.values()),
            "zones": [
                {
                    "name": zone.name,
                    "unique_people": len(self._visitors[zone.name]),
                    "entries": self._entries[zone.name],
                    "peak_people": self._peak_in_zone[zone.name],
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
