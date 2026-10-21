
import cv2
import numpy as np

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt


class VideoWidget(QLabel):
    def __init__(self):
        super().__init__()

        self.setObjectName("videoDisplay")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Ожидание видеопотока...")

        self.last_frame = None

    def update_frame(self, frame: np.ndarray):
        self.last_frame = frame
        self._display_frame(frame)

    def _display_frame(self, frame: np.ndarray):
        """Отображает видеокадр с сохранением пропорций."""
        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w

        q_image = QImage(
            rgb_frame.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )

        pixmap = QPixmap.fromImage(q_image)

        scaled_pixmap = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Перерисовывает последний кадр после изменения размера."""
        super().resizeEvent(event)

        if self.last_frame is not None:
            self._display_frame(self.last_frame)
