# src/gui/heatmap_widget.py
import cv2
import numpy as np
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt


class HeatmapWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #1e1e1e; color: white; border-radius: 5px;")
        self.setText("Ожидание данных тепловой карты...")
        self.last_heatmap = None  # Сохраняем последнюю тепловую карту

    def update_heatmap(self, heatmap_img: np.ndarray):
        self.last_heatmap = heatmap_img  # Сохраняем для последующего resize
        self._display_heatmap(heatmap_img)

    def _display_heatmap(self, heatmap_img: np.ndarray):
        """Внутренний метод для отрисовки тепловой карты."""
        rgb_img = cv2.cvtColor(heatmap_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        
        q_image = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        scaled_pixmap = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Перерисовываем последнюю тепловую карту при изменении размера окна."""
        super().resizeEvent(event)
        if self.last_heatmap is not None:
            self._display_heatmap(self.last_heatmap)