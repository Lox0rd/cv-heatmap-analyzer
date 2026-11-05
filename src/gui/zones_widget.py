"""Interactive editor for polygon zones on a video frame."""

from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.zones.zone_manager import ZoneManager
from src.zones.zone_store import ZoneStore


class ZoneCanvas(QLabel):
    point_added = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.setObjectName("zoneCanvas")
        self.setMinimumSize(380, 280)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.frame = None
        self.image = None
        self.zones = []
        self.draft = []
        self.editing = False
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_frame(self, frame: np.ndarray | None) -> None:
        self.frame = frame.copy() if frame is not None else None
        if self.frame is None:
            self.image = None
        else:
            rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb.shape
            self.image = QImage(
                rgb.data, width, height, channels * width, QImage.Format.Format_RGB888
            ).copy()
        self.render_frame()

    def image_rect(self) -> QRectF:
        if self.image is None:
            return QRectF()
        scale = min(self.width() / self.image.width(), self.height() / self.image.height())
        width = self.image.width() * scale
        height = self.image.height() * scale
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    def frame_point(self, position: QPointF) -> tuple[int, int] | None:
        rect = self.image_rect()
        if rect.isEmpty() or not rect.contains(position):
            return None
        x = int((position.x() - rect.left()) * self.image.width() / rect.width())
        y = int((position.y() - rect.top()) * self.image.height() / rect.height())
        return min(x, self.image.width() - 1), min(y, self.image.height() - 1)

    def mousePressEvent(self, event):
        if self.editing and event.button() == Qt.MouseButton.LeftButton:
            point = self.frame_point(event.position())
            if point is not None:
                self.point_added.emit(*point)
                return
        super().mousePressEvent(event)

    def render_frame(self):
        if self.width() <= 0 or self.height() <= 0:
            return
        pixmap = QPixmap(self.size())
        pixmap.fill(QColor("#112C43"))
        painter = QPainter(pixmap)
        if self.image is None:
            painter.setPen(QColor("#A9C2D4"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Загрузите кадр для разметки зон")
            painter.end()
            self.setPixmap(pixmap)
            return

        rect = self.image_rect()
        painter.drawImage(rect, self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        def display_point(point):
            x, y = point
            return QPointF(
                rect.left() + x * rect.width() / self.image.width(),
                rect.top() + y * rect.height() / self.image.height(),
            )

        for zone in self.zones:
            polygon = QPolygonF([display_point(point) for point in zone.points])
            painter.setPen(QPen(QColor("#40D9FF"), 2))
            painter.setBrush(QColor(0, 117, 190, 58))
            painter.drawPolygon(polygon)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(display_point(zone.points[0]) + QPointF(8, -8), zone.name)

        if self.draft:
            painter.setPen(QPen(QColor("#FFD166"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(QPolygonF([display_point(point) for point in self.draft]))
            painter.setBrush(QColor("#FFD166"))
            for point in self.draft:
                painter.drawEllipse(display_point(point), 4, 4)
        painter.end()
        self.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.render_frame()


class ZonesWidget(QWidget):
    frame_requested = pyqtSignal()
    zones_changed = pyqtSignal()

    def __init__(self, store: ZoneStore | None = None):
        super().__init__()
        default_path = Path(__file__).resolve().parents[2] / "data" / "output" / "zones.json"
        self.store = store or ZoneStore(default_path)
        self.manager = ZoneManager()
        self.source = None
        self.frame_size = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(20)

        viewer = QFrame()
        viewer.setObjectName("viewerPanel")
        viewer_layout = QVBoxLayout(viewer)
        viewer_layout.setContentsMargins(20, 18, 20, 20)
        viewer_layout.setSpacing(12)
        heading = QLabel("Разметка зон интереса")
        heading.setObjectName("sectionTitle")
        viewer_layout.addWidget(heading)
        self.canvas = ZoneCanvas()
        self.canvas.point_added.connect(self._add_point)
        viewer_layout.addWidget(self.canvas, stretch=1)
        self.hint = QLabel("Выберите источник на вкладке «Анализ», затем загрузите кадр.")
        self.hint.setObjectName("zoneHint")
        self.hint.setWordWrap(True)
        viewer_layout.addWidget(self.hint)
        layout.addWidget(viewer, stretch=1)

        controls = QFrame()
        controls.setObjectName("zoneControls")
        controls.setFixedWidth(300)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(18, 18, 18, 18)
        controls_layout.setSpacing(10)
        controls_title = QLabel("Список зон")
        controls_title.setObjectName("sectionTitle")
        controls_layout.addWidget(controls_title)
        self.zone_list = QListWidget()
        self.zone_list.setObjectName("zoneList")
        self.zone_list.currentItemChanged.connect(lambda *_: self._update_controls())
        controls_layout.addWidget(self.zone_list, stretch=1)

        self.load_btn = QPushButton("Загрузить кадр")
        self.load_btn.clicked.connect(self.frame_requested.emit)
        controls_layout.addWidget(self.load_btn)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название зоны")
        controls_layout.addWidget(self.name_input)
        self.new_btn = QPushButton("Новая зона")
        self.new_btn.clicked.connect(self.begin_zone)
        controls_layout.addWidget(self.new_btn)
        self.undo_btn = QPushButton("Отменить точку")
        self.undo_btn.setObjectName("secondaryButton")
        self.undo_btn.clicked.connect(self.undo_point)
        controls_layout.addWidget(self.undo_btn)
        self.save_btn = QPushButton("Сохранить зону")
        self.save_btn.clicked.connect(self.save_zone)
        controls_layout.addWidget(self.save_btn)
        self.cancel_btn = QPushButton("Сбросить разметку")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.cancel_zone)
        controls_layout.addWidget(self.cancel_btn)
        self.delete_btn = QPushButton("Удалить выбранную")
        self.delete_btn.setObjectName("secondaryButton")
        self.delete_btn.clicked.connect(self.delete_zone)
        controls_layout.addWidget(self.delete_btn)
        controls_layout.addStretch()
        layout.addWidget(controls)
        self._update_controls()

    def set_context(self, source: str, frame: np.ndarray) -> None:
        height, width = frame.shape[:2]
        if source != self.source or (width, height) != self.frame_size:
            try:
                self.manager = self.store.load(source, width, height)
            except (OSError, ValueError, KeyError, TypeError) as error:
                self.manager = ZoneManager()
                QMessageBox.warning(self, "Зоны", f"Не удалось загрузить зоны: {error}")
            self.source = source
            self.frame_size = (width, height)
            self._refresh_zones()
        self.canvas.set_frame(frame)
        self.cancel_zone()
        self.hint.setText("Нажмите «Новая зона» и отметьте на кадре минимум три вершины.")

    def clear_context(self, message: str) -> None:
        self.source = None
        self.frame_size = None
        self.manager = ZoneManager()
        self.canvas.set_frame(None)
        self.cancel_zone()
        self._refresh_zones()
        self.hint.setText(message)

    def begin_zone(self) -> None:
        if self.canvas.frame is None:
            self.hint.setText("Сначала загрузите кадр из выбранного источника.")
            return
        self.canvas.draft = []
        self.canvas.editing = True
        if not self.name_input.text().strip():
            self.name_input.setText(f"Зона {len(self.manager.get_zones()) + 1}")
        self.hint.setText("Щёлкайте по кадру, чтобы добавить вершины многоугольника.")
        self.canvas.render_frame()
        self._update_controls()

    def _add_point(self, x: int, y: int) -> None:
        self.canvas.draft.append((x, y))
        self.canvas.render_frame()
        self._update_controls()

    def undo_point(self) -> None:
        if self.canvas.draft:
            self.canvas.draft.pop()
            self.canvas.render_frame()
            self._update_controls()

    def cancel_zone(self) -> None:
        self.canvas.editing = False
        self.canvas.draft = []
        self.canvas.render_frame()
        self._update_controls()

    def save_zone(self) -> None:
        name = self.name_input.text().strip()
        try:
            zone = self.manager.add_zone(name, self.canvas.draft)
        except ValueError as error:
            QMessageBox.warning(self, "Зоны", str(error))
            return
        try:
            self.store.save(self.source, *self.frame_size, self.manager.get_zones())
        except (OSError, ValueError, TypeError) as error:
            self.manager.remove_zone(zone.name)
            QMessageBox.warning(self, "Зоны", str(error))
            return
        self.cancel_zone()
        self.name_input.clear()
        self._refresh_zones()
        self.hint.setText(f"Зона «{zone.name}» сохранена.")
        self.zones_changed.emit()

    def delete_zone(self) -> None:
        item = self.zone_list.currentItem()
        if item is None:
            return
        name = item.text()
        zone = self.manager.get_zone(name)
        self.manager.remove_zone(name)
        try:
            self.store.save(self.source, *self.frame_size, self.manager.get_zones())
        except (OSError, ValueError) as error:
            self.manager.add_zone(zone.name, list(zone.points))
            QMessageBox.warning(self, "Зоны", str(error))
            return
        self._refresh_zones()
        self.hint.setText(f"Зона «{name}» удалена.")
        self.zones_changed.emit()

    def _refresh_zones(self) -> None:
        self.canvas.zones = self.manager.get_zones()
        self.zone_list.clear()
        self.zone_list.addItems([zone.name for zone in self.canvas.zones])
        self.canvas.render_frame()
        self._update_controls()

    def _update_controls(self) -> None:
        drawing = self.canvas.editing
        self.undo_btn.setEnabled(drawing and bool(self.canvas.draft))
        self.save_btn.setEnabled(drawing and len(self.canvas.draft) >= 3)
        self.cancel_btn.setEnabled(drawing)
        self.delete_btn.setEnabled(bool(self.zone_list.currentItem()))
