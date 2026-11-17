"""Export the latest available video analysis results."""

import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.export.data_exporter import (
    export_json,
    export_timeline_csv,
    export_zones_csv,
    read_statistics,
)
from src.export.image_exporter import export_png
from src.export.report_generator import export_pdf


def _modified(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns if path.is_file() else None
    except OSError:
        return None


class ExportWidget(QWidget):
    def __init__(self, commentary_provider, parent=None):
        super().__init__(parent)
        self.commentary_provider = commentary_provider
        self._actions = []
        self._busy = False
        self._map_path = self._overlay_path = self._statistics_path = None
        self._protected_paths = ()
        self._source_key = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        panel = QFrame()
        panel.setObjectName("viewerPanel")
        content = QVBoxLayout(panel)
        content.setContentsMargins(18, 16, 18, 16)
        content.setSpacing(10)
        layout.addWidget(panel)

        title = QLabel("Экспорт результатов")
        title.setObjectName("sectionTitle")
        content.addWidget(title)
        for label, hint, name, kind, callback in (
            (
                "PDF",
                "Отчёт с картой, статистикой и готовым текстом анализа.",
                "activity-report.pdf",
                "report",
                self._export_report,
            ),
            (
                "CSV",
                "Посетители, входы и пиковая загрузка по зонам",
                "zones.csv",
                "statistics",
                export_zones_csv,
            ),
            (
                "CSV",
                "Число людей и входы по секундам",
                "timeline.csv",
                "statistics",
                export_timeline_csv,
            ),
            (
                "JSON",
                "Сводка, статистика зон и данные по времени",
                "statistics.json",
                "statistics",
                export_json,
            ),
            ("PNG", "Тепловая карта", "heatmap.png", "map", export_png),
            (
                "PNG",
                "Кадр с наложением тепловой карты",
                "heatmap-overlay.png",
                "overlay",
                export_png,
            ),
        ):
            row = QHBoxLayout()
            description = QLabel(hint)
            description.setWordWrap(True)
            row.addWidget(description, stretch=1)
            button = QPushButton(f"Сохранить {label}")
            button.setAccessibleName(f"{button.text()} — {hint}")
            button.setMinimumWidth(150)
            button.setEnabled(False)
            button.clicked.connect(
                lambda _checked=False, b=button, n=name, k=kind, fn=callback: (
                    self._save(b, n, k, fn)
                )
            )
            row.addWidget(button)
            self._actions.append((button, kind))
            content.addLayout(row)

        self.status_label = QLabel("Сначала запустите анализ видео.")
        self.status_label.setObjectName("zoneHint")
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def begin_processing(self):
        self._busy = True
        self._update_controls()

    def refresh(self, output_dir: Path, statistics_path: Path):
        self._busy = False
        raw = output_dir / "heatmap_raw.jpg"
        overlay = output_dir / "heatmap_overlay.jpg"
        metadata_path = output_dir / "heatmap_overlay.source.json"
        self._protected_paths = (
            raw,
            overlay,
            metadata_path,
            statistics_path,
            output_dir / "zones.json",
        )
        raw_time, overlay_time, stats_time = map(
            _modified, (raw, overlay, statistics_path)
        )
        metadata = {}
        if (
            overlay_time is not None
            and (metadata_time := _modified(metadata_path)) is not None
            and metadata_time >= overlay_time
        ):
            try:
                value = json.loads(metadata_path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    metadata = value
            except (OSError, ValueError):
                pass

        self._overlay_path = overlay if overlay_time is not None else None
        self._map_path = (
            raw
            if raw_time is not None
            and (overlay_time is None or raw_time <= overlay_time)
            and metadata.get("raw_available") is not False
            else None
        )
        self._statistics_path = (
            statistics_path
            if stats_time is not None
            and (overlay_time is None or stats_time >= overlay_time)
            and metadata.get("statistics_available") is not False
            else None
        )
        self._source_key = metadata.get("source_key")
        self._update_controls()

    def _update_controls(self):
        enabled = {
            "map": self._map_path is not None,
            "overlay": self._overlay_path is not None,
            "statistics": self._statistics_path is not None,
            "report": self._overlay_path is not None
            or self._statistics_path is not None,
        }
        for button, kind in self._actions:
            button.setEnabled(enabled[kind] and not self._busy)
        if self._busy:
            status = "Экспорт станет доступен после завершения обработки видео."
        elif any(enabled.values()):
            status = "Выберите формат, чтобы сохранить результаты последней обработки."
        else:
            status = "Сначала запустите анализ видео."
        self.status_label.setText(status)

    def _read_statistics(self):
        data = read_statistics(self._statistics_path)
        if self._source_key is not None and data.get("source_key") != self._source_key:
            raise ValueError("Статистика относится к другому видео. Повторите анализ.")
        return data

    def _export_report(self, destination: Path):
        statistics = self._read_statistics() if self._statistics_path else None
        commentary = (
            self.commentary_provider(self._overlay_path) if self._overlay_path else None
        )
        export_pdf(destination, self._overlay_path, statistics, commentary)

    def _save(self, button, filename, kind, callback):
        if not button.isEnabled():
            return
        suffix = Path(filename).suffix
        dialog = QFileDialog(self, "Сохранить результаты", filename)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter(f"{suffix[1:].upper()} (*{suffix})")
        dialog.setDefaultSuffix(suffix[1:])
        if not dialog.exec() or not button.isEnabled():
            return

        path = Path(dialog.selectedFiles()[0])
        try:
            if path.suffix.lower() != suffix:
                raise ValueError(f"Укажите имя файла с расширением {suffix}.")
            if path.resolve() in {item.resolve() for item in self._protected_paths}:
                raise ValueError(
                    "Выберите другое имя, чтобы сохранить исходные данные."
                )
            if kind == "report":
                callback(path)
            elif kind == "statistics":
                callback(self._read_statistics(), path)
            else:
                callback(self._map_path if kind == "map" else self._overlay_path, path)
        except (OSError, ValueError, RuntimeError) as error:
            self.status_label.setText(f"Не удалось сохранить файл. {error}")
        else:
            self.status_label.setText(f"Сохранено: {path}")
