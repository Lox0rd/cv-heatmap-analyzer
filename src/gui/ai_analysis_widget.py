"""Send a heatmap-overlay frame and the configured prompt to the vision model."""

from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ai.vision_api import VisionAPI
from src.config.settings import AI_ANALYSIS_PROMPT
from src.gui.heatmap_widget import HeatmapWidget
from src.zones.overlay import draw_zones


class VisionAnalysisThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, frame: np.ndarray, prompt: str):
        super().__init__()
        self.frame = frame.copy()
        self.prompt = prompt

    def run(self):
        try:
            response = VisionAPI().analyze_frame(self.frame, self.prompt)
            self.response_ready.emit(response or "Модель не вернула текст.")
        except Exception as error:
            self.error_occurred.emit(str(error))


class AIAnalysisWidget(QWidget):
    def __init__(self, output_dir: Path | None = None, zones_provider=None, prompt_provider=None):
        super().__init__()
        self.output_dir = Path(output_dir or Path("data/output"))
        self.zones_provider = zones_provider or (lambda frame: [])
        self.prompt_provider = prompt_provider or (lambda: AI_ANALYSIS_PROMPT)
        self.overlay_frame = None
        self.zones = []
        self.worker = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(20)

        image_panel = QFrame()
        image_panel.setObjectName("viewerPanel")
        image_layout = QVBoxLayout(image_panel)
        image_layout.setContentsMargins(18, 18, 18, 18)
        image_layout.setSpacing(12)
        image_title = QLabel("Кадр для анализа")
        image_title.setObjectName("sectionTitle")
        image_layout.addWidget(image_title)
        self.image_display = HeatmapWidget()
        self.image_display.setMinimumSize(280, 240)
        image_layout.addWidget(self.image_display, stretch=1)
        self.image_status = QLabel("Запустите анализ, чтобы создать кадр с тепловой картой.")
        self.image_status.setObjectName("zoneHint")
        self.image_status.setWordWrap(True)
        image_layout.addWidget(self.image_status)
        self.refresh_btn = QPushButton("Обновить кадр")
        self.refresh_btn.clicked.connect(self.refresh_frame)
        image_layout.addWidget(self.refresh_btn)
        layout.addWidget(image_panel, stretch=3)

        prompt_panel = QFrame()
        prompt_panel.setObjectName("viewerPanel")
        prompt_layout = QVBoxLayout(prompt_panel)
        prompt_layout.setContentsMargins(18, 18, 18, 18)
        prompt_layout.setSpacing(12)
        prompt_title = QLabel("Запрос к модели")
        prompt_title.setObjectName("sectionTitle")
        prompt_layout.addWidget(prompt_title)
        prompt_hint = QLabel(
            "Промпт задаётся в «Настройках». Номера и названия отмеченных зон "
            "добавляются к нему автоматически."
        )
        prompt_hint.setObjectName("zoneHint")
        prompt_hint.setWordWrap(True)
        prompt_layout.addWidget(prompt_hint)
        self.analyze_btn = QPushButton("Анализировать кадр")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.start_analysis)
        prompt_layout.addWidget(self.analyze_btn)
        result_title = QLabel("Ответ модели")
        result_title.setObjectName("sectionTitle")
        prompt_layout.addWidget(result_title)
        self.result_output = QTextEdit()
        self.result_output.setObjectName("resultOutput")
        self.result_output.setReadOnly(True)
        self.result_output.setPlaceholderText("Здесь появится результат анализа.")
        prompt_layout.addWidget(self.result_output, stretch=1)
        self.status_label = QLabel("Ожидание кадра.")
        self.status_label.setObjectName("zoneHint")
        self.status_label.setWordWrap(True)
        prompt_layout.addWidget(self.status_label)
        layout.addWidget(prompt_panel, stretch=2)

    def refresh_frame(self) -> bool:
        if self._is_running():
            return self.overlay_frame is not None
        path = self.output_dir / "heatmap_overlay.jpg"
        frame = cv2.imread(str(path)) if path.is_file() else None
        if frame is None:
            self.overlay_frame = None
            self.zones = []
            self.image_display.set_placeholder("Кадр с тепловой картой пока не создан")
            self.image_status.setText("Сначала запустите анализ видео.")
            self.status_label.setText("Ожидание кадра.")
        else:
            try:
                self.zones = list(self.zones_provider(frame))
            except (OSError, ValueError, KeyError, TypeError) as error:
                self.overlay_frame = None
                self.image_display.set_placeholder("Не удалось загрузить зоны")
                self.image_status.setText(str(error))
                self.status_label.setText("Проверьте файл зон.")
                self.analyze_btn.setEnabled(False)
                return False
            self.overlay_frame = draw_zones(frame, self.zones)
            self.image_display.update_heatmap(self.overlay_frame)
            self.image_status.setText(
                f"Будет отправлен кадр: {path.name}. Отмечено зон: {len(self.zones)}."
            )
            self.status_label.setText("Кадр готов к анализу.")
        self.analyze_btn.setEnabled(self.overlay_frame is not None)
        return self.overlay_frame is not None

    def _is_running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def start_analysis(self) -> None:
        if self._is_running():
            return
        prompt = self.prompt_provider().strip()
        if not prompt:
            self.status_label.setText("Введите промпт для анализа.")
            return
        if self.overlay_frame is None:
            self.status_label.setText("Сначала постройте тепловую карту.")
            return
        if self.zones:
            legend = "; ".join(
                f"{number} — {zone.name}"
                for number, zone in enumerate(self.zones, start=1)
            )
            prompt += (
                "\n\nКонтуры с номерами на кадре обозначают зоны интереса: "
                f"{legend}. Учитывай их в выводах."
            )
        self.result_output.clear()
        self.status_label.setText("Кадр и промпт отправляются модели...")
        self.analyze_btn.setEnabled(False)
        self.worker = VisionAnalysisThread(self.overlay_frame, prompt)
        self.worker.response_ready.connect(self._show_response)
        self.worker.error_occurred.connect(self._show_error)
        self.worker.finished.connect(self._finish_analysis)
        self.worker.start()

    def _show_response(self, response: str) -> None:
        self.result_output.setPlainText(response)
        self.status_label.setText("Анализ завершён.")

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"Ошибка анализа: {message}")

    def _finish_analysis(self) -> None:
        self.analyze_btn.setEnabled(self.overlay_frame is not None)
