from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
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
        self.resize(1360, 820)
        self.setMinimumSize(940, 620)

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
            style = style_path.read_text(encoding="utf-8")
            style = style.replace(
                "resources/styles/selected.svg",
                (style_path.parent / "selected.svg").as_posix(),
            )
            app.setStyleSheet(style)
        else:
            print(
                f"[WARNING] Файл стилей не найден: {style_path}"
            )

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root = QVBoxLayout(central_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("appHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(28, 15, 28, 15)

        identity = QVBoxLayout()
        identity.setSpacing(2)
        eyebrow = QLabel("СИСТЕМА ВИДЕОАНАЛИТИКИ")
        eyebrow.setObjectName("headerEyebrow")
        title = QLabel("Мониторинг активности")
        title.setObjectName("headerTitle")
        identity.addWidget(eyebrow)
        identity.addWidget(title)
        header_layout.addLayout(identity)
        header_layout.addStretch()
        module = QLabel("ТЕПЛОВАЯ КАРТА  /  АНАЛИЗ ВИДЕО")
        module.setObjectName("headerModule")
        header_layout.addWidget(module)
        root.addWidget(header)

        workspace = QWidget()
        workspace.setObjectName("workspace")
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(22, 22, 22, 22)
        workspace_layout.setSpacing(20)
        root.addWidget(workspace, stretch=1)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(320)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_title = QLabel("Параметры анализа")
        sidebar_title.setObjectName("sectionTitle")
        sidebar_title.setContentsMargins(18, 18, 18, 12)
        sidebar_layout.addWidget(sidebar_title)

        self.settings_widget = SettingsWidget()
        settings_scroll = QScrollArea()
        settings_scroll.setObjectName("settingsScroll")
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setWidget(self.settings_widget)
        sidebar_layout.addWidget(settings_scroll, stretch=1)
        workspace_layout.addWidget(sidebar)

        viewer = QFrame()
        viewer.setObjectName("viewerPanel")
        viewer_layout = QVBoxLayout(viewer)
        viewer_layout.setContentsMargins(20, 18, 20, 20)
        viewer_layout.setSpacing(14)

        viewer_heading = QHBoxLayout()
        viewer_title = QLabel("Видеопоток")
        viewer_title.setObjectName("sectionTitle")
        viewer_heading.addWidget(viewer_title)
        viewer_heading.addStretch()
        viewer_badge = QLabel("●  ОБЛАСТЬ ПРОСМОТРА")
        viewer_badge.setObjectName("viewerBadge")
        viewer_heading.addWidget(viewer_badge)
        viewer_layout.addLayout(viewer_heading)

        self.video_widget = VideoWidget()
        self.video_widget.setMinimumSize(320, 240)
        viewer_layout.addWidget(self.video_widget, stretch=1)
        viewer_layout.addWidget(self.settings_widget.seek_group)
        workspace_layout.addWidget(viewer, stretch=1)


        # Сигналы анализа.
        self.settings_widget.start_requested.connect(self.start_processing)
        self.settings_widget.stop_requested.connect(self.stop_processing)
        self.settings_widget.preview_play_requested.connect(self.play_preview)
        self.settings_widget.seek_requested.connect(self._on_seek)

    # === Предпросмотр видео ===
    def play_preview(self):
        """Запускает воспроизведение или переключает паузу."""
        if self.thread and self.thread.isRunning():
            self.settings_widget.set_status("Предпросмотр недоступен во время анализа.")
            return

        if self.settings_widget.source_type_combo.currentData() != "file":
            self.settings_widget.set_status(
                "Предпросмотр доступен только для видеофайлов."
            )
            return

        source = self.settings_widget.source_input.text().strip()
        if not source:
            self.settings_widget.set_status("Сначала выберите видеофайл.")
            return

        if self.preview_thread is not None and self.preview_thread.isRunning():
            playing = self.preview_thread.toggle_playback()
            self.settings_widget.set_preview_playing(playing)
            return

        start_frame = self.settings_widget.seek_slider.value()
        total_frames = self.settings_widget._total_frames

        if total_frames > 0 and start_frame >= total_frames - 1:
            start_frame = 0

        self.preview_thread = VideoPreviewThread(source, start_frame=start_frame)

        self.preview_thread.frame_ready.connect(self.video_widget.update_frame)
        self.preview_thread.position_changed.connect(self.settings_widget.set_current_frame)
        self.preview_thread.total_frames_changed.connect(self.settings_widget.set_total_frames)
        self.preview_thread.error_occurred.connect(self.settings_widget.set_status)
        self.preview_thread.playback_finished.connect(self._on_preview_finished)

        self.settings_widget.set_preview_playing(True)
        self.settings_widget.set_status("Воспроизведение видео...")
        self.preview_thread.start()

    def _on_preview_finished(self):
        self.settings_widget.set_preview_playing(False)
        self.settings_widget.set_status("Предпросмотр завершён.")

    def _stop_preview(self):
        if self.preview_thread is not None and self.preview_thread.isRunning():
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
        selected_objects: list | None = None,
    ):
        self._stop_preview()
        self.settings_widget.set_analysis_running(True)
        self.video_widget.set_placeholder("Обработка видео...")
        self.settings_widget.set_status("Запуск обработки...")
        self.settings_widget.set_seek_enabled(False)

        self.thread = ProcessingThread(
            sources=sources,
            confidence=confidence,
            alpha=alpha,
            skip_frames=skip_frames,
            colormap_name=colormap_name,
            show_detections=show_detections,
            show_heatmap=show_heatmap,
            selected_objects=selected_objects,
        )

        self.thread.frame_ready.connect(self.video_widget.update_frame)
        self.thread.status_update.connect(self.settings_widget.set_status)
        self.thread.frame_position_changed.connect(self.settings_widget.set_current_frame)
        self.thread.total_frames_changed.connect(self.settings_widget.set_total_frames)
        self.thread.is_file_source.connect(self.settings_widget.set_seek_enabled)
        self.thread.finished.connect(self.on_finished)

        self.thread.start()

    # === Перемотка ===
    def _on_seek(self, frame_index: int):
        """Передаёт перемотку активному потоку."""
        if self.preview_thread is not None and self.preview_thread.isRunning():
            self.preview_thread.seek(frame_index)
            return
        if self.thread and self.thread.isRunning():
            self.thread.seek(frame_index)

    # === Остановка анализа ===
    def stop_processing(self):
        if self.thread and self.thread.isRunning():
            self.settings_widget.set_status("Остановка анализа...")
            self.thread.stop()

    def on_finished(self):
        self.settings_widget.set_analysis_running(False)
        self.settings_widget.set_status(
            "Обработка завершена. Тепловая карта: data/output/heatmap.jpg"
        )
        self.settings_widget.start_btn.setEnabled(True)
        self.settings_widget.stop_btn.setEnabled(False)
        self.settings_widget._set_source_controls_enabled(True)
        self.settings_widget.play_btn.setEnabled(
            self.settings_widget.source_type_combo.currentData() == "file"
        )

    def closeEvent(self, event):
        self._stop_preview()
        if self.thread and self.thread.isRunning():
            self.stop_processing()
        event.accept()
