import numpy as np

from src.detection import detector as detector_module
from src.detection.detector import YOLODetector


class FakeTensor:
    def __init__(self, value):
        self.value = value

    def tolist(self):
        return self.value

    def item(self):
        return self.value


class FakeBox:
    def __init__(self, bbox, class_id, confidence):
        self.xyxy = [FakeTensor(list(bbox))]
        self.cls = FakeTensor(class_id)
        self.conf = FakeTensor(confidence)


class FakeResult:
    boxes = [FakeBox((1.8, 2.2, 30.9, 40.1), 2, 0.91)]
    names = {2: "car"}


class FakeModel:
    def __init__(self):
        self.predict_kwargs = None

    def predict(self, **kwargs):
        self.predict_kwargs = kwargs
        return [FakeResult()]


def test_detector_uses_model_path_and_detection_defaults(monkeypatch):
    loaded_models = []
    monkeypatch.setattr(
        detector_module,
        "YOLO",
        lambda path: loaded_models.append(path) or FakeModel(),
    )

    detector = YOLODetector()
    frame = np.zeros((20, 20, 3), dtype=np.uint8)
    detections = detector.detect(frame)

    assert loaded_models == ["models/yolo26n.pt"]
    assert detector.model.predict_kwargs["source"] is frame
    assert detector.model.predict_kwargs["classes"] == [0, 2, 1, 3, 5, 7]
    assert detector.model.predict_kwargs["conf"] == 0.5
    assert detections == [
        {
            "label": "car",
            "class_id": 2,
            "confidence": 0.91,
            "bbox": (1, 2, 30, 40),
        }
    ]


def test_detector_passes_custom_classes_and_confidence(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(detector_module, "YOLO", lambda _: model)
    detector = YOLODetector("custom.pt")

    detector.detect(
        np.zeros((5, 5, 3), dtype=np.uint8),
        objects=["truck", "cat"],
        confidence=0.8,
    )

    assert model.predict_kwargs["classes"] == [7]
    assert model.predict_kwargs["conf"] == 0.8


def test_detector_returns_empty_when_model_finds_no_boxes(monkeypatch):
    model = FakeModel()
    model.predict = lambda **_: [type("Result", (), {"boxes": [], "names": {}})()]
    monkeypatch.setattr(detector_module, "YOLO", lambda _: model)

    detections = YOLODetector("custom.pt").detect(
        np.zeros((5, 5, 3), dtype=np.uint8),
        objects=[],
    )

    assert detections == []
