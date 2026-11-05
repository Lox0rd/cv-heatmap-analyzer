"""Local storage for polygon zones associated with a video source."""

import json
from pathlib import Path

from src.zones.zone_manager import Zone, ZoneManager


class ZoneStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Файл зон имеет неверный формат")
        return data

    def load(self, source: str, width: int, height: int) -> ZoneManager:
        manager = ZoneManager()
        record = self._read().get(source)
        if record is None:
            return manager
        if record.get("size") != [width, height]:
            return manager
        for item in record.get("zones", []):
            manager.add_zone(item["name"], item["points"])
        return manager

    def save(self, source: str, width: int, height: int, zones: list[Zone]) -> None:
        data = self._read()
        data[source] = {
            "size": [width, height],
            "zones": [
                {"name": zone.name, "points": [list(point) for point in zone.points]}
                for zone in zones
            ],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)
