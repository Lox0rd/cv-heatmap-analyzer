from ultralytics import YOLO


class YOLODetector:
    # Идентификаторы классов стандартной модели COCO
    CLASSES = {
        "person": 0,
        "bicycle": 1,
        "car": 2,
        "motorcycle": 3,
        "bus": 5,
        "truck": 7,
    }

    def __init__(self, model_path="models/yolo26n.pt"):
        self.model = YOLO(model_path)

    def detect(self, frame, objects=None, confidence=0.5):
        if objects is None:
            objects = ["person", "car", "bicycle", "motorcycle", "bus", "truck"]

        class_ids = [
            self.CLASSES[name]
            for name in objects
            if name in self.CLASSES
        ]

        results = self.model.predict(
            source=frame,
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

            detections.append({
                "label": results[0].names[class_id],
                "class_id": class_id,
                "confidence": float(box.conf.item()),
                "bbox": (x1, y1, x2, y2),
            })

        return detections
