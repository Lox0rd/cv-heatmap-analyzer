import numpy as np
import pytest

from src.gui import processing_thread as processing_module
from src.gui.processing_thread import ProcessingThread


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

    def draw_text(self, *args, **kwargs):
        self.drawn.append(("text", args, kwargs))

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
        assert objects is None
        assert confidence == 0.5
        return self.detections


class FakeRenderer:
    def __init__(self):
        self.saved = False
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
    monkeypatch.setattr(processing_module.time, "time", lambda: 10.0)

    thread = ProcessingThread(
        sources=["sample.mp4"],
        confidence=0.5,
        alpha=0.6,
        skip_frames=0,
        colormap_name="Missing",
        show_detections=show_detections,
        show_heatmap=show_heatmap,
    )
    thread.status_update.connect(statuses.append)
    thread.frame_ready.connect(frames.append)
    thread.run()

    assert len(frames) == 1
    assert video.released
    assert renderer.saved == (
        "data/output/heatmap.jpg",
        processing_module.cv2.COLORMAP_JET,
    )
    assert bool(renderer.overlays) is show_heatmap
    if expected_overlay is not None:
        assert renderer.overlays == [
            (expected_overlay, processing_module.cv2.COLORMAP_JET)
        ]
    if show_detections:
        assert [entry[0] for entry in video.drawn] == ["rectangle", "text"]
    assert any("Обработано 1 кадров" in status for status in statuses)


def test_processing_thread_reports_open_source_error(monkeypatch):
    statuses = []
    monkeypatch.setattr(
        processing_module.VideoProcessor,
        "open_source",
        lambda _: (_ for _ in ()).throw(RuntimeError("source failed")),
    )
    thread = ProcessingThread(["bad"], 0.5, 0.5, 0)
    thread.status_update.connect(statuses.append)

    thread.run()

    assert any("source failed" in status for status in statuses)
