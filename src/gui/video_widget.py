# src/gui/video_widget.py
import cv2
import numpy as np
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt


class VideoWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background-color: #2c395e; "
            "color: #bdc3c7; "
            "border-radius: 5px; "
            "font-size: 24px; "
            "font-weight: bold;"
        )
        self.setText("Ожидание видеопотока...")
        self.last_frame = None  # Сохраняем последний кадр для перерисовки при resize

    def update_frame(self, frame: np.ndarray):
        self.last_frame = frame  # Сохраняем для последующего resize
        self._display_frame(frame)

    def _display_frame(self, frame: np.ndarray):
        """Внутренний метод для отрисовки кадра."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        # Создаем QImage из numpy-массива
        q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        # Масштабируем под размер виджета
        scaled_pixmap = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Перерисовываем последний кадр при изменении размера окна."""
        super().resizeEvent(event)
        if self.last_frame is not None:
            self._display_frame(self.last_frame)