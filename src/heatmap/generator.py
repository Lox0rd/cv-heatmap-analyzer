import cv2
import numpy as np


class HeatmapGenerator:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

        self.heatmap = np.zeros(
            (height, width),
            dtype=np.float32,
        )

    def update(self, detections):
        """Добавляет обнаружения на тепловую карту."""
        for obj in detections:
            x1, y1, x2, y2 = obj["bbox"]

            x = (x1 + x2) // 2
            y = y2

            if 0 <= x < self.width and 0 <= y < self.height:
                cv2.circle(
                    self.heatmap,
                    (x, y),
                    radius=10,
                    color=1.0,
                    thickness=-1,
                )

    def get_heatmap(self):
        """Возвращает матрицу накопленных значений."""
        return self.heatmap