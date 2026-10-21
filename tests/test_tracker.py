
import numpy as np

from src.detection.detector import YOLODetector
from src.detection.tracker import ObjectTracker


class FakeTensor:
    def __init__(self, value):
        self.value = value

    def tolist(self):
        return self.value

    def item(self):
        return self.value


class FakeBox:
    def __init__(self, bbox, class_id, confidence, track_id=None):
        self.xyxy = [FakeTensor(list(bbox))]
        self.cls = FakeTensor(class_id)
        self.conf = FakeTensor(confidence)
        self.id = FakeTensor(track_id) if track_id is not None else None


class FakeResult:
    def __init__(self, boxes, names=None):
        self.boxes = boxes
        self.names = names or {
            0: "person",
            1: "bicycle",
            2: "car",
            3: "motorcycle",
            5: "bus",
            7: "truck",
        }


class FakeTrackingModel:
    def __init__(self, results=None):
        self.results = results if results is not None else [FakeResult([])]
        self.track_kwargs = None

    def track(self, **kwargs):
        self.track_kwargs = kwargs
        return self.results


class FakeDetector:
    CLASSES = YOLODetector.CLASSES

    def __init__(self, model):
        self.model = model


def make_tracker(boxes=None):
    """Создаёт трекер с поддельной моделью вместо настоящей YOLO."""
    model = FakeTrackingModel([FakeResult(boxes or [])])
    detector = FakeDetector(model)
    return ObjectTracker(detector=detector), model


def test_tracker_uses_injected_detector():
    tracker, _ = make_tracker()

    assert isinstance(tracker, ObjectTracker)


def test_tracker_returns_formatted_detection_with_track_id():
    box = FakeBox((10.9, 20.2, 100.8, 200.5), 0, 0.95, track_id=42)
    tracker, _ = make_tracker([box])

    detections = tracker.update(
        np.zeros((240, 320, 3), dtype=np.uint8)
    )

    assert detections == [
        {
            "label": "person",
            "class_id": 0,
            "confidence": 0.95,
            "bbox": (10, 20, 100, 200),
            "track_id": 42,
        }
    ]


def test_tracker_returns_none_when_track_id_is_missing():
    box = FakeBox((10, 20, 100, 200), 2, 0.88)
    tracker, _ = make_tracker([box])

    detections = tracker.update(
        np.zeros((240, 320, 3), dtype=np.uint8)
    )

    assert len(detections) == 1
    assert detections[0]["label"] == "car"
    assert detections[0]["track_id"] is None


def test_tracker_uses_default_objects_and_confidence():
    tracker, model = make_tracker()
    frame = np.zeros((10, 10, 3), dtype=np.uint8)

    tracker.update(frame)

    assert model.track_kwargs["source"] is frame
    assert model.track_kwargs["classes"] == [0, 2]
    assert model.track_kwargs["conf"] == 0.5
    assert model.track_kwargs["persist"] is True
    assert model.track_kwargs["tracker"] == "bytetrack.yaml"
    assert model.track_kwargs["verbose"] is False


def test_tracker_passes_custom_objects_and_confidence():
    tracker, model = make_tracker()
    frame = np.zeros((10, 10, 3), dtype=np.uint8)

    tracker.update(
        frame,
        objects=["truck", "bicycle"],
        confidence=0.75,
    )

    assert model.track_kwargs["source"] is frame
    assert model.track_kwargs["classes"] == [7, 1]
    assert model.track_kwargs["conf"] == 0.75


def test_tracker_ignores_unknown_object_names():
    tracker, model = make_tracker()

    tracker.update(
        np.zeros((10, 10, 3), dtype=np.uint8),
        objects=["person", "cat", "car"],
    )

    assert model.track_kwargs["classes"] == [0, 2]


def test_tracker_passes_empty_class_list_for_unknown_objects():
    tracker, model = make_tracker()

    detections = tracker.update(
        np.zeros((10, 10, 3), dtype=np.uint8),
        objects=["cat", "dog"],
    )

    assert detections == []
    assert model.track_kwargs["classes"] == []


def test_tracker_returns_empty_list_when_no_objects_found():
    tracker, _ = make_tracker()

    detections = tracker.update(
        np.zeros((10, 10, 3), dtype=np.uint8)
    )

    assert detections == []


def test_tracker_returns_multiple_objects_with_separate_ids():
    boxes = [
        FakeBox((1, 2, 30, 40), 0, 0.91, track_id=5),
        FakeBox((50, 60, 90, 100), 2, 0.87, track_id=9),
    ]
    tracker, _ = make_tracker(boxes)

    detections = tracker.update(
        np.zeros((120, 120, 3), dtype=np.uint8)
    )

    assert len(detections) == 2
    assert detections[0]["label"] == "person"
    assert detections[0]["track_id"] == 5
    assert detections[1]["label"] == "car"
    assert detections[1]["track_id"] == 9
