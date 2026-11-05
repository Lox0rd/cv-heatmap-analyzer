import json

from src.analysis.zone_statistics import ZoneStatistics
from src.zones.zone_manager import Zone


def person(track_id, x1, x2, y2=30):
    return {"label": "person", "track_id": track_id, "bbox": (x1, 10, x2, y2)}


def test_people_are_counted_once_per_frame_and_only_on_zone_entry(tmp_path):
    zone = Zone("Вход", ((40, 0), (90, 0), (90, 50), (40, 50)))
    stats = ZoneStatistics([zone], fps=2, source_key="file:video.mp4")

    assert stats.add_frame(0, [
        person(1, 5, 15),
        person(None, 5, 15),
        {"label": "car", "track_id": 99, "bbox": (50, 10, 60, 30)},
    ]) == 2
    assert stats.add_frame(1, [
        person(1, 50, 60), person(1, 50, 60), person(2, 70, 80),
    ]) == 2
    stats.add_frame(2, [person(1, 50, 60), person(2, 5, 15)])
    stats.add_frame(3, [person(1, 5, 15), person(2, 70, 80)])
    stats.add_frame(4, [person(1, 50, 60)])

    result = stats.to_dict()
    assert result["version"] == 2
    assert result["frames_processed"] == 5
    assert result["person_observations"] == 9
    assert result["untracked_person_observations"] == 1
    assert result["unique_people"] == 2
    assert result["peak_people_in_frame"] == 2
    assert result["total_zone_entries"] == 3
    assert result["zones"] == [{
        "name": "Вход", "unique_people": 2, "entries": 3, "peak_people": 2
    }]
    assert [item["zone_entries"]["Вход"] for item in result["timeline"]] == [1, 1, 1]
    assert [item["people_in_frame_peak"] for item in result["timeline"]] == [2, 2, 1]

    path = tmp_path / "statistics.json"
    stats.save(path)
    assert json.loads(path.read_text(encoding="utf-8")) == result


def test_first_sighting_inside_is_visitor_but_not_observed_entry():
    zone = Zone("Вход", ((0, 0), (50, 0), (50, 50), (0, 50)))
    stats = ZoneStatistics([zone], fps=10, source_key="camera:0")
    stats.add_frame(0, [person(7, 10, 20), person(None, 20, 30)])
    stats.add_frame(1, [person(7, 10, 20)])

    assert stats.to_dict()["zones"] == [{
        "name": "Вход", "unique_people": 1, "entries": 0, "peak_people": 2
    }]


def test_empty_frames_and_zero_fps_are_supported():
    stats = ZoneStatistics([], fps=0, source_key="camera:0")
    assert stats.add_frame(0, []) == 0

    assert stats.to_dict()["timeline"] == [{
        "second": 0, "people_in_frame_peak": 0,
        "zone_people_peak": {}, "zone_entries": {},
    }]
