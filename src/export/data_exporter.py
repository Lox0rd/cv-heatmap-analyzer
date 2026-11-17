"""Export the saved zone statistics in tabular and structured formats."""

import csv
import io
import json
from pathlib import Path

from src.export import save_bytes

ZONE_FIELDS = ("name", "unique_people", "entries", "peak_people")
SUMMARY_FIELDS = (
    "frames_processed",
    "unique_people",
    "peak_people_in_frame",
    "total_zone_entries",
)


def read_statistics(path: Path) -> dict:
    """Load the current statistics format and validate fields used in exports."""
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        if data["version"] != 2:
            raise ValueError("Формат статистики устарел. Запустите анализ повторно.")
        zones = data["zones"]
        timeline = data["timeline"]
        if not isinstance(zones, list) or not isinstance(timeline, list):
            raise TypeError
        _check_counts(data, SUMMARY_FIELDS)
        for zone in zones:
            if not isinstance(zone["name"], str):
                raise TypeError
            _check_counts(zone, ZONE_FIELDS[1:])
        for point in timeline:
            _check_counts(point, ("second", "people_in_frame_peak"))
            for key in ("zone_people_peak", "zone_entries"):
                if not isinstance(point[key], dict):
                    raise TypeError
                _check_counts(point[key], point[key])
    except (KeyError, TypeError) as error:
        raise ValueError(
            "Файл статистики повреждён. Запустите анализ повторно."
        ) from error
    return data


def _check_counts(record, keys):
    if any(type(record[key]) is not int or record[key] < 0 for key in keys):
        raise TypeError


def export_json(data: dict, destination: Path) -> None:
    # The internal source key can contain a local path or RTSP credentials.
    public_data = {key: value for key, value in data.items() if key != "source_key"}
    payload = json.dumps(public_data, ensure_ascii=False, indent=2) + "\n"
    save_bytes(destination, payload.encode("utf-8"))


def _spreadsheet_text(value: str) -> str:
    if value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(
        ("=", "+", "-", "@", "＝", "＋", "－", "＠")
    ):
        return "'" + value
    return value


def _write_csv(destination: Path, headings, rows) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(headings)
    writer.writerows(rows)
    save_bytes(destination, buffer.getvalue().encode("utf-8-sig"))


def export_zones_csv(data: dict, destination: Path) -> None:
    rows = (
        (_spreadsheet_text(zone["name"]), *(zone[key] for key in ZONE_FIELDS[1:]))
        for zone in data["zones"]
    )
    _write_csv(destination, ("Зона", "Посетители по ID", "Входы", "Пик людей"), rows)


def export_timeline_csv(data: dict, destination: Path) -> None:
    names = [zone["name"] for zone in data["zones"]]
    headings = ["Секунда", "Пик людей в кадре"]
    for name in names:
        headings.extend((f"Пик в зоне {name}", f"Входы в зону {name}"))

    def rows():
        for point in data["timeline"]:
            row = [point["second"], point["people_in_frame_peak"]]
            for name in names:
                row.extend(
                    (
                        point["zone_people_peak"].get(name, 0),
                        point["zone_entries"].get(name, 0),
                    )
                )
            yield row

    _write_csv(destination, headings, rows())
