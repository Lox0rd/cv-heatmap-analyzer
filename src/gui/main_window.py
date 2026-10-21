
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from src.gui.preview_thread import VideoPreviewThread
from src.gui.processing_thread import ProcessingThread
from src.gui.settings_widget import SettingsWidget
from src.gui.video_widget import VideoWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CV Heatmap Analyzer")
        self.resize(1200, 700)

        self.thread = None
        self.preview_thread = None

        self._load_styles()
        self._init_ui()

    def _load_styles(self):
        """Загружает стили из внешнего QSS-файла."""
        style_path = (
            Path(__file__).resolve().parents[2]
            / "resources"
            / "styles"
            / "style.qss"
        )

        app = QApplication.instance()

        if app is not None and style_path.is_file():
            app.setStyleSheet(
                style_path.read_text(encoding="utf-8")
            )
        else:
            print(
                f"[WARNING] Файл стилей не найден: {style_path}"
            )

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)

        self.video_widget = VideoWidget()
        left_layout.addWidget(self.video_widget, stretch=1)

        self.settings_widget = SettingsWidget()

        # Перемещаем группу предпросмотра под видеовиджет.
        left_layout.addWidget(
            self.settings_widget.seek_group,
            stretch=0,
        )

        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addWidget(
            self.settings_widget,
            stretch=1,
        )

        # Сигналы анализа.
        self.settings_widget.start_requested.connect(
            self.start_processing
        )
        self.settings_widget.stop_requested.connect(
            self.stop_processing
        )

        # Сигналы предпросмотра.
        self.settings_widget.preview_play_requested.connect(
            self.play_preview
        )
        self.settings_widget.seek_requested.connect(
            self._on_seek
        )

    # === Предпросмотр видео ===
    def play_preview(self):
        """Запускает воспроизведение или переключает паузу."""
        if self.thread and self.thread.isRunning():
            self.settings_widget.set_status(
                "Предпросмотр недоступен во время анализа."
            )
            return

        if (
            self.settings_widget.source_type_combo.currentData()
            != "file"
        ):
            self.settings_widget.set_status(
                "Предпросмотр доступен только для видеофайлов."
            )
            return

        source = (
            self.settings_widget.source_input.text().strip()
        )

        if not source:
            self.settings_widget.set_status(
                "Сначала выберите видеофайл."
            )
            return

        # Если поток предпросмотра работает — Play/Pause.
        if (
            self.preview_thread is not None
            and self.preview_thread.isRunning()
        ):
            playing = self.preview_thread.toggle_playback()
            self.settings_widget.set_preview_playing(playing)
            return

        # Если дошли до последнего кадра, начинаем сначала.
        start_frame = self.settings_widget.seek_slider.value()
        total_frames = self.settings_widget._total_frames

        if total_frames > 0 and start_frame >= total_frames - 1:
            start_frame = 0

        self.preview_thread = VideoPreviewThread(
            source,
            start_frame=start_frame,
        )

        self.preview_thread.frame_ready.connect(
            self.video_widget.update_frame
        )
        self.preview_thread.position_changed.connect(
            self.settings_widget.set_current_frame
        )
        self.preview_thread.total_frames_changed.connect(
            self.settings_widget.set_total_frames
        )
        self.preview_thread.error_occurred.connect(
            self.settings_widget.set_status
        )
        self.preview_thread.playback_finished.connect(
            self._on_preview_finished
        )

        self.settings_widget.set_preview_playing(True)
        self.settings_widget.set_status(
            "Воспроизведение видео..."
        )

        self.preview_thread.start()

    def _on_preview_finished(self):
        self.settings_widget.set_preview_playing(False)
        self.settings_widget.set_status(
            "Предпросмотр завершён."
        )

    def _stop_preview(self):
        if (
            self.preview_thread is not None
            and self.preview_thread.isRunning()
        ):
            self.preview_thread.stop()

        self.preview_thread = None
        self.settings_widget.set_preview_playing(False)

    # === Полный анализ ===
    def start_processing(
        self,
        sources: list,
        confidence: float,
        alpha: float,
        skip_frames: int,
        colormap_name: str,
        show_detections: bool,
        show_heatmap: bool,
    ):
        # Предпросмотр и анализ не должны работать одновременно.
        self._stop_preview()
        self.settings_widget.set_analysis_running(True)

        self.settings_widget.set_status(
            "Запуск обработки..."
        )
        self.settings_widget.set_seek_enabled(False)

        self.thread = ProcessingThread(
            sources=sources,
            confidence=confidence,
            alpha=alpha,
            skip_frames=skip_frames,
            colormap_name=colormap_name,
            show_detections=show_detections,
            show_heatmap=show_heatmap,
        )

        self.thread.frame_ready.connect(
            self.video_widget.update_frame
        )
        self.thread.status_update.connect(
            self.settings_widget.set_status
        )
        self.thread.frame_position_changed.connect(
            self.settings_widget.set_current_frame
        )
        self.thread.total_frames_changed.connect(
            self.settings_widget.set_total_frames
        )
        self.thread.is_file_source.connect(
            self.settings_widget.set_seek_enabled
        )
        self.thread.finished.connect(self.on_finished)

        self.thread.start()

    # === Перемотка ===
    def _on_seek(self, frame_index: int):
        """Передаёт перемотку активному потоку."""
        if (
            self.preview_thread is not None
            and self.preview_thread.isRunning()
        ):
            self.preview_thread.seek(frame_index)
            return

        if self.thread and self.thread.isRunning():
            self.thread.seek(frame_index)

    # === Остановка анализа ===
    def stop_processing(self):
        if self.thread and self.thread.isRunning():
            self.settings_widget.set_status(
                "Остановка анализа..."
            )
            self.thread.stop()

    def on_finished(self):
        self.settings_widget.set_analysis_running(False)
        self.settings_widget.set_status(
            "Обработка завершена. "
            "Тепловая карта: data/output/heatmap.jpg"
        )

        self.settings_widget.start_btn.setEnabled(True)
        self.settings_widget.stop_btn.setEnabled(False)

        self.settings_widget._set_source_controls_enabled(
            True
        )

        self.settings_widget.play_btn.setEnabled(
            self.settings_widget.source_type_combo.currentData()
            == "file"
        )

    def closeEvent(self, event):
        self._stop_preview()

        if self.thread and self.thread.isRunning():
            self.stop_processing()

        event.accept()
