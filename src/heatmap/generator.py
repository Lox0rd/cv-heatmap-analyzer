# src/heatmap/generator.py
import cv2
import numpy as np


class HeatmapGenerator:
    def __init__(self, width: int, height: int, decay: float = 0.995):
        """
        :param width: Ширина кадра
        :param height: Высота кадра
        :param decay: Коэффициент затухания (0.999 = медленное 
        затухание, 0.95 = быстрое).
                      Значение 1.0 отключает затухание.
        """
        self.width = width
        self.height = height
        self.decay = decay
        
        self.heatmap = np.zeros((height, width), dtype=np.float32)

    def update(self, detections):
        """Добавляет обнаружения на тепловую карту с оптимизацией."""
        if not detections:
            return

        # Векторизованное извлечение координат
        bboxes = np.array([obj["bbox"] for obj in detections], dtype=np.int32)
        
        # Вычисляем нижнюю центральную точку (x, y)
        x_coords = (bboxes[:, 0] + bboxes[:, 2]) // 2
        y_coords = bboxes[:, 3]  # y2

        # Векторизованная фильтрация границ
        valid_mask = (x_coords >= 0) & (x_coords < self.width) & \
                     (y_coords >= 0) & (y_coords < self.height)
        
        valid_x = x_coords[valid_mask]
        valid_y = y_coords[valid_mask]

        # Быстрое добавление значений
        for x, y in zip(valid_x, valid_y):
            cv2.circle(self.heatmap, (int(x), int(y)), radius=10, color=1.0, 
                       thickness=-1)

    def apply_decay(self):
        """Затухание тепловой карты (вызывать каждый кадр)."""
        if self.decay < 1.0:
            self.heatmap *= self.decay

    def get_heatmap(self):
        """Возвращает матрицу накопленных значений."""
        return self.heatmap

    def reset(self):
        """Очистка тепловой карты."""
        self.heatmap.fill(0.0)