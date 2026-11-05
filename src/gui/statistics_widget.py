"""Table and charts for activity collected during video processing."""

import json
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


CHART_COLORS = ("#0075BE", "#E28B32", "#44A998", "#9275C8", "#D45E71")


class ActivityChart(QLabel):
    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind
        self.timeline = []
        self.zones = []
        self.setMinimumHeight(145)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_data(self, timeline: list[dict], zones: list[dict]) -> None:
        self.timeline = timeline
        self.zones = zones
        self.render_chart()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.render_chart()

    def render_chart(self):
        if self.width() <= 0 or self.height() <= 0:
            return
        canvas = QPixmap(self.size())
        canvas.fill(QColor("#FFFFFF"))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#71899B"))
        if not self.timeline and not self.zones:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет данных для графика")
        elif self.kind == "timeline":
            self._draw_timeline(painter)
        else:
            self._draw_zones(painter)
        painter.end()
        self.setPixmap(canvas)

    def _draw_timeline(self, painter: QPainter):
        if not self.timeline:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет активности по времени")
            return
        left, top = 45, 30
        right, bottom = self.width() - 20, self.height() - 35
        width, height = max(1, right - left), max(1, bottom - top)
        maximum = max(1, max(row["total"] for row in self.timeline))
        seconds = [row["second"] for row in self.timeline]
        first, last = min(seconds), max(seconds)
        span = max(1, last - first)
        painter.setPen(QPen(QColor("#DDE8EF"), 1))
        for step in range(5):
            y = bottom - height * step / 4
            painter.drawLine(QPointF(left, y), QPointF(right, y))
            painter.setPen(QColor("#71899B"))
            painter.drawText(2, int(y) + 4, str(round(maximum * step / 4)))
            painter.setPen(QPen(QColor("#DDE8EF"), 1))
        painter.setPen(QColor("#71899B"))
        painter.drawText(left, self.height() - 8, f"{first} с")
        painter.drawText(right - 35, self.height() - 8, f"{last} с")

        series = [("Всего", "total", CHART_COLORS[0])]
        visible_count = max(1, min(4, (self.width() - left) // 105 - 1))
        visible_zones = sorted(
            self.zones, key=lambda zone: zone["observations"], reverse=True
        )[:visible_count]
        series.extend(
            (zone["name"], zone["name"], CHART_COLORS[(index + 1) % len(CHART_COLORS)])
            for index, zone in enumerate(visible_zones)
        )
        for index, (name, key, color) in enumerate(series):
            points = []
            for row in self.timeline:
                value = row["total"] if key == "total" else row["zones"].get(key, 0)
                x = left + (row["second"] - first) * width / span
                y = bottom - value * height / maximum
                points.append(QPointF(x, y))
            painter.setPen(QPen(QColor(color), 2))
            if len(points) == 1:
                painter.drawEllipse(points[0], 3, 3)
            else:
                painter.drawPolyline(QPolygonF(points))
            painter.drawText(left + index * 105, 17, name[:15])

    def _draw_zones(self, painter: QPainter):
        if not self.zones:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Сначала добавьте зоны")
            return
        zones = sorted(self.zones, key=lambda zone: zone["observations"], reverse=True)[:8]
        maximum = max(1, max(zone["observations"] for zone in zones))
        top, row_height = 22, max(22, (self.height() - 32) // len(zones))
        bar_left = min(150, self.width() // 3)
        bar_width = max(10, self.width() - bar_left - 65)
        for index, zone in enumerate(zones):
            y = top + index * row_height
            painter.setPen(QColor("#18324A"))
            painter.drawText(12, y + 14, zone["name"][:20])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#E8F4FB"))
            painter.drawRoundedRect(bar_left, y, bar_width, 17, 3, 3)
            value_width = int(bar_width * zone["observations"] / maximum)
            painter.setBrush(QColor(CHART_COLORS[index % len(CHART_COLORS)]))
            if value_width:
                painter.drawRoundedRect(bar_left, y, value_width, 17, 3, 3)
            painter.setPen(QColor("#18324A"))
            painter.drawText(bar_left + bar_width + 8, y + 14, str(zone["observations"]))


class StatisticsWidget(QWidget):
    def __init__(self, statistics_path: Path | None = None):
        super().__init__()
        self.statistics_path = Path(statistics_path or "data/output/zone_statistics.json")
        self.data = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        heading = QHBoxLayout()
        title = QLabel("Статистика активности")
        title.setObjectName("sectionTitle")
        heading.addWidget(title)
        heading.addStretch()
        self.refresh_btn = QPushButton("Обновить данные")
        self.refresh_btn.clicked.connect(self.refresh)
        heading.addWidget(self.refresh_btn)
        layout.addLayout(heading)

        summary = QHBoxLayout()
        summary.setSpacing(14)
        self.frames_value = self._summary_card(summary, "Обработано кадров")
        self.observations_value = self._summary_card(summary, "Наблюдений объектов")
        self.zones_value = self._summary_card(summary, "Зон интереса")
        layout.addLayout(summary)

        content = QHBoxLayout()
        content.setSpacing(20)
        charts = QVBoxLayout()
        charts.setSpacing(16)
        self.timeline_chart = ActivityChart("timeline")
        self.zone_chart = ActivityChart("zones")
        for name, chart in (
            ("Активность по времени", self.timeline_chart),
            ("Наблюдения по зонам", self.zone_chart),
        ):
            panel = QFrame()
            panel.setObjectName("viewerPanel")
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(16, 14, 16, 14)
            label = QLabel(name)
            label.setObjectName("sectionTitle")
            panel_layout.addWidget(label)
            panel_layout.addWidget(chart, stretch=1)
            charts.addWidget(panel, stretch=1)
        content.addLayout(charts, stretch=3)

        table_panel = QFrame()
        table_panel.setObjectName("viewerPanel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(16, 14, 16, 14)
        table_title = QLabel("Таблица по зонам")
        table_title.setObjectName("sectionTitle")
        table_layout.addWidget(table_title)
        self.zone_table = QTableWidget(0, 3)
        self.zone_table.setHorizontalHeaderLabels(["Зона", "Наблюдений", "Объектов"])
        self.zone_table.horizontalHeader().setStretchLastSection(True)
        self.zone_table.verticalHeader().setVisible(False)
        self.zone_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.zone_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_layout.addWidget(self.zone_table)
        content.addWidget(table_panel, stretch=2)
        layout.addLayout(content, stretch=1)

        self.status_label = QLabel("Запустите анализ для построения статистики.")
        self.status_label.setObjectName("zoneHint")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    @staticmethod
    def _summary_card(layout, title):
        panel = QFrame()
        panel.setObjectName("statCard")
        inner = QVBoxLayout(panel)
        caption = QLabel(title)
        caption.setObjectName("statCaption")
        value = QLabel("0")
        value.setObjectName("statValue")
        inner.addWidget(caption)
        inner.addWidget(value)
        layout.addWidget(panel, stretch=1)
        return value

    def refresh(self) -> bool:
        if not self.statistics_path.is_file():
            self._clear("Статистика появится после анализа видео.")
            return False
        try:
            data = json.loads(self.statistics_path.read_text(encoding="utf-8"))
            if data.get("version") != 1:
                raise ValueError("Неподдерживаемый формат статистики")
            zones = data["zones"]
            timeline = data["timeline"]
            frames = data["frames_processed"]
            observations = data["total_observations"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._clear(f"Не удалось загрузить статистику: {error}")
            return False
        self.data = data
        self.frames_value.setText(str(frames))
        self.observations_value.setText(str(observations))
        self.zones_value.setText(str(len(zones)))
        self.zone_table.setRowCount(len(zones))
        for row, zone in enumerate(zones):
            for column, value in enumerate((
                zone["name"], zone["observations"], zone["unique_objects"]
            )):
                self.zone_table.setItem(row, column, QTableWidgetItem(str(value)))
        self.timeline_chart.set_data(timeline, zones)
        self.zone_chart.set_data(timeline, zones)
        message = "Показаны результаты последнего анализа. Наблюдение — объект в одном кадре."
        if len(zones) > 4:
            message += " График времени показывает до 4 самых активных зон."
        if len(zones) > 8:
            message += " Столбчатый график показывает 8 самых активных зон; таблица — все зоны."
        self.status_label.setText(message)
        return True

    def _clear(self, message: str):
        self.data = None
        self.frames_value.setText("0")
        self.observations_value.setText("0")
        self.zones_value.setText("0")
        self.zone_table.setRowCount(0)
        self.timeline_chart.set_data([], [])
        self.zone_chart.set_data([], [])
        self.status_label.setText(message)
