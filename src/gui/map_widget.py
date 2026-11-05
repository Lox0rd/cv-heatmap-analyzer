"""Viewer for the heatmap images produced by video analysis."""

from pathlib import Path

import cv2
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.heatmap_widget import HeatmapWidget


class MapWidget(QWidget):
    def __init__(self, output_dir: Path | None = None, refresh_action=None):
        super().__init__()
        self.output_dir = Path(output_dir or Path("data/output"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        heading = QHBoxLayout()
        title = QLabel("Тепловая карта активности")
        title.setObjectName("sectionTitle")
        heading.addWidget(title)
        heading.addStretch()
        self.refresh_btn = QPushButton("Обновить карту")
        self.refresh_btn.clicked.connect(refresh_action or self.refresh)
        heading.addWidget(self.refresh_btn)
        layout.addLayout(heading)

        content = QHBoxLayout()
        content.setSpacing(20)
        self.raw_display = HeatmapWidget()
        self.overlay_display = HeatmapWidget()
        for name, display in (
            ("Тепловая карта", self.raw_display),
            ("Наложение на кадр", self.overlay_display),
        ):
            panel = QFrame()
            panel.setObjectName("viewerPanel")
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(18, 18, 18, 18)
            panel_layout.setSpacing(12)
            panel_title = QLabel(name)
            panel_title.setObjectName("sectionTitle")
            panel_layout.addWidget(panel_title)
            display.setMinimumSize(260, 220)
            panel_layout.addWidget(display, stretch=1)
            content.addWidget(panel, stretch=1)
        layout.addLayout(content, stretch=1)

        self.status_label = QLabel("Запустите анализ, чтобы построить карту.")
        self.status_label.setObjectName("zoneHint")
        layout.addWidget(self.status_label)

    def refresh(self) -> bool:
        found = 0
        for name, display in (
            ("heatmap_raw.jpg", self.raw_display),
            ("heatmap_overlay.jpg", self.overlay_display),
        ):
            path = self.output_dir / name
            image = cv2.imread(str(path)) if path.is_file() else None
            if image is None:
                display.set_placeholder("Карта пока не построена")
            else:
                display.update_heatmap(image)
                found += 1
        self.status_label.setText(
            "Показаны результаты последнего анализа."
            if found == 2
            else "Нет результатов анализа. Проверьте источник видео и запустите анализ."
        )
        return found == 2
