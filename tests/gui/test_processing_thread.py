import json

import numpy as np
import pytest

from src.gui import processing_thread as processing_module
from src.gui.processing_thread import ProcessingThread
from src.zones.zone_manager import ZoneManager
from src.zones.zone_store import ZoneStore


class FakeVideo:
    def __init__(self, frame, source_type="file"):
        self.frame = frame
        self.drawn = []
        self.source_type = source_type

    def get_info(self):
        return {
            "source_value": "sample.mp4",
            "width": self.frame.shape[1],
            "height": self.frame.shape[0],
            "fps": 30,
            "source_type": self.source_type,
            "frame_count": 1,
        }

    def read_frames(self, skip_frames):
        assert skip_frames == 0
        return iter([self.frame.copy()])

    def get_current_frame_index(self):
        return 0

    def draw_rectangle(self, *args, **kwargs):
        self.drawn.append(("rectangle", args, kwargs))
        args[0][0, 0] = 255

    def draw_text(self, *args, **kwargs):
        self.drawn.append(("text", args, kwargs))
        args[0][0, 1] = 255

    def release(self):
        self.released = True


class FakeTracker:
    def __init__(self, _detector):
        self.detections = [{
            "bbox": (1, 2, 8, 9),
            "label": "person",
            "track_id": 4,
            "confidence": 0.9,
        }]

    def update(self, frame, objects, confidence):
        assert objects == ["person"]
        assert confidence == 0.5
        return self.detections


class FakeRenderer:
    def __init__(self):
        self.overlays = []

    def overlay(self, frame, heatmap, alpha, colormap):
        self.overlays.append((alpha, colormap))
        return frame

    def save(self, heatmap, output_path, colormap):
        self.saved = (output_path, colormap)


@pytest.mark.parametrize(
    ("show_detections", "show_heatmap", "expected_overlay"),
    [(True, True, 0.6), (False, True, 1.0), (True, False, None)],
)
def test_processing_thread_processes_frame_and_saves_heatmap(
    monkeypatch, show_detections, show_heatmap, expected_overlay
):
    frame = np.zeros((12, 16, 3), dtype=np.uint8)
    video = FakeVideo(frame)
    renderer = FakeRenderer()
    statuses = []
    frames = []
    saved_images = []
    result_paths = []
    monkeypatch.setattr(
        processing_module.VideoProcessor,
        "open_source",
        lambda sources: video,
    )
    monkeypatch.setattr(processing_module, "YOLODetector", lambda: object())
    monkeypatch.setattr(processing_module, "ObjectTracker", FakeTracker)
    monkeypatch.setattr(
        processing_module, "HeatmapRenderer", lambda: renderer
    )
    monkeypatch.setattr(
        processing_module.cv2,
        "imwrite",
        lambda path, image: saved_images.append((path, image)) or True,
    )
    monkeypatch.setattr(processing_module.time, "time", lambda: 10.0)

    thread = ProcessingThread(
        sources=["sample.mp4"],
        confidence=0.5,
        alpha=0.6,
        skip_frames=0,
        colormap_name="Missing",
        show_detections=show_detections,
        show_heatmap=show_heatmap,
        selected_objects=["person"],
    )
    thread.status_update.connect(statuses.append)
    thread.frame_ready.connect(frames.append)
    thread.result_saved.connect(result_paths.append)
    thread.run()

    assert len(frames) == 1
    assert video.released
    assert saved_images[0][0] == "data/output/heatmap_overlay.jpg"
    assert renderer.saved[0] == "data/output/heatmap_raw.jpg"
    assert result_paths == ["data/output/heatmap_overlay.jpg"]
    assert np.count_nonzero(saved_images[0][1][0, :2]) == 0
    assert len(renderer.overlays) == (2 if show_heatmap else 1)
    assert renderer.overlays[-1] == (
        0.6,
        processing_module.cv2.COLORMAP_JET,
    )
    if expected_overlay is not None and show_heatmap:
        assert renderer.overlays[0] == (
            expected_overlay,
            processing_module.cv2.COLORMAP_JET,
        )
    if show_detections:
        assert [entry[0] for entry in video.drawn] == ["rectangle"]
    assert any("Обработано 1 кадров" in status for status in statuses)


def test_processing_thread_reports_open_source_error(monkeypatch):
    statuses = []
    result_paths = []
    monkeypatch.setattr(
        processing_module.VideoProcessor,
        "open_source",
        lambda _: (_ for _ in ()).throw(RuntimeError("source failed")),
    )
    thread = ProcessingThread(["bad"], 0.5, 0.5, 0)
    thread.status_update.connect(statuses.append)
    thread.result_saved.connect(result_paths.append)

    thread.run()

    assert any("source failed" in status for status in statuses)
    assert result_paths == []


def test_processing_thread_saves_zone_statistics(monkeypatch, tmp_path):
    frame = np.zeros((12, 16, 3), dtype=np.uint8)
    video = FakeVideo(frame)
    zones = ZoneManager()
    zones.add_zone("Вход", [(0, 0), (15, 0), (15, 11), (0, 11)])
    zone_path = tmp_path / "zones.json"
    statistics_path = tmp_path / "zone_statistics.json"
    ZoneStore(zone_path).save("file:sample.mp4", 16, 12, zones.get_zones())
    monkeypatch.setattr(processing_module.VideoProcessor, "open_source", lambda _: video)
    monkeypatch.setattr(processing_module, "YOLODetector", lambda: object())
    monkeypatch.setattr(processing_module, "ObjectTracker", FakeTracker)
    monkeypatch.setattr(processing_module, "HeatmapRenderer", FakeRenderer)
    monkeypatch.setattr(processing_module.cv2, "imwrite", lambda *_: True)
    paths = []
    people_counts = []
    thread = ProcessingThread(
        sources=["sample.mp4"], confidence=0.5, alpha=0.6, skip_frames=0,
        selected_objects=["person"], source_key="file:sample.mp4",
        zone_store_path=zone_path, statistics_path=statistics_path,
    )
    thread.statistics_saved.connect(paths.append)
    thread.people_count_updated.connect(people_counts.append)

    thread.run()

    assert paths == [str(statistics_path)]
    assert people_counts == [1]
    result = json.loads(statistics_path.read_text(encoding="utf-8"))
    assert result["zones"][0] == {
        "name": "Вход", "unique_people": 1, "entries": 0, "peak_people": 1
    }
    assert result["timeline"][0]["zone_people_peak"] == {"Вход": 1}


def test_stream_statistics_use_elapsed_time(monkeypatch, tmp_path):
    frame = np.zeros((12, 16, 3), dtype=np.uint8)
    video = FakeVideo(frame, source_type="rtsp")
    video.read_frames = lambda skip_frames: iter([frame.copy(), frame.copy()])
    monkeypatch.setattr(processing_module.VideoProcessor, "open_source", lambda _: video)
    monkeypatch.setattr(processing_module, "YOLODetector", lambda: object())
    monkeypatch.setattr(processing_module, "ObjectTracker", FakeTracker)
    monkeypatch.setattr(processing_module, "HeatmapRenderer", FakeRenderer)
    monkeypatch.setattr(processing_module.cv2, "imwrite", lambda *_: True)
    clock = iter([10.0, 10.0, 12.0, 13.0])
    monkeypatch.setattr(processing_module.time, "time", lambda: next(clock))
    statistics_path = tmp_path / "zone_statistics.json"
    thread = ProcessingThread(
        ["rtsp://camera"], 0.5, 0.6, 0, selected_objects=["person"],
        source_key="rtsp:rtsp://camera", statistics_path=statistics_path,
        zone_store_path=tmp_path / "missing-zones.json",
    )

    thread.run()

    timeline = json.loads(statistics_path.read_text(encoding="utf-8"))["timeline"]
    assert [row["second"] for row in timeline] == [0, 2]
