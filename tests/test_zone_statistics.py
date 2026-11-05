import json

from src.analysis.zone_statistics import ZoneStatistics
from src.zones.zone_manager import Zone


def test_counts_observations_tracks_and_activity_by_second(tmp_path):
    zones = [
        Zone("Вход", ((0, 0), (50, 0), (50, 50), (0, 50))),
        Zone("Выход", ((50, 0), (100, 0), (100, 50), (50, 50))),
    ]
    stats = ZoneStatistics(zones, fps=10, source_key="file:video.mp4")
    stats.add_frame(0, [
        {"bbox": (10, 10, 20, 30), "track_id": 1, "label": "person"},
        {"bbox": (70, 10, 80, 30), "track_id": 2, "label": "person"},
    ])
    stats.add_frame(10, [
        {"bbox": (10, 10, 20, 30), "track_id": 1, "label": "person"},
        {"bbox": (110, 10, 120, 30), "track_id": 3, "label": "person"},
    ])

    result = stats.to_dict()
    assert result["total_observations"] == 4
    assert result["frames_processed"] == 2
    assert result["zones"] == [
        {"name": "Вход", "observations": 2, "unique_objects": 1},
        {"name": "Выход", "observations": 1, "unique_objects": 1},
    ]
    assert result["timeline"] == [
        {"second": 0, "total": 2, "zones": {"Вход": 1, "Выход": 1}},
        {"second": 1, "total": 2, "zones": {"Вход": 1, "Выход": 0}},
    ]
    path = tmp_path / "statistics.json"
    stats.save(path)
    assert json.loads(path.read_text(encoding="utf-8")) == result


def test_empty_frames_and_zero_fps_are_supported():
    stats = ZoneStatistics([], fps=0, source_key="camera:0")
    stats.add_frame(0, [])

    assert stats.to_dict()["timeline"] == [{"second": 0, "total": 0, "zones": {}}]
