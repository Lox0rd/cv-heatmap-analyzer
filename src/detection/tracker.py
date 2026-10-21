from src.config.settings import DETECTION_CONFIDENCE, TRACKED_OBJECTS
from src.detection.detector import YOLODetector


class ObjectTracker:
    def __init__(self, detector=None):
        self.detector = detector or YOLODetector()

    def update(self, frame, objects=None, confidence=DETECTION_CONFIDENCE):
        if objects is None:
            objects = TRACKED_OBJECTS

        class_ids = [
            self.detector.CLASSES[name]
            for name in objects
            if name in self.detector.CLASSES
        ]

        results = self.detector.model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=class_ids,
            conf=confidence,
            verbose=False,
        )

        detections = []

        for box in results[0].boxes:
            x1, y1, x2, y2 = map(
                int, box.xyxy[0].tolist()
            )

            class_id = int(box.cls.item())

            track_id = None
            if box.id is not None:
                track_id = int(box.id.item())

            detections.append({
                "label": results[0].names[class_id],
                "class_id": class_id,
                "confidence": float(box.conf.item()),
                "bbox": (x1, y1, x2, y2),
                "track_id": track_id,
            })

        return detections
