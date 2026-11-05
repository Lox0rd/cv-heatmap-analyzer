from pathlib import Path

import cv2
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.gui.preview_thread import VideoPreviewThread
from src.gui.processing_thread import ProcessingThread
from src.gui.settings_widget import SettingsWidget
from src.gui.video_widget import VideoWidget
from src.gui.zones_widget import ZonesWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CV Heatmap Analyzer")
        self.resize(1360, 820)
        self.setMinimumSize(940, 620)

        self.thread = None
        self.preview_thread = None
        self._display_source_key = None
        self._zones_loaded_for = None

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
        self.settings_button = QPushButton("Настройки")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.clicked.connect(self._show_settings)
        header_layout.addWidget(self.settings_button)
        module = QLabel("ТЕПЛОВАЯ КАРТА  /  АНАЛИЗ ВИДЕО")
        module.setObjectName("headerModule")
        header_layout.addWidget(module)
        root.addWidget(header)

        workspace = QWidget()
        workspace.setObjectName("workspace")
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(22, 22, 22, 22)
        workspace_layout.setSpacing(20)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        root.addWidget(self.tabs, stretch=1)
        self.tabs.addTab(workspace, "Анализ")
        self.zones_widget = ZonesWidget()
        self.zones_widget.frame_requested.connect(self._load_zone_frame)
        self.zones_widget.zones_changed.connect(self._on_zones_changed)
        self.tabs.addTab(self.zones_widget, "Зоны")
        for name in ("Карта", "Статистика", "AI анализ", "Экспорт"):
            page = QWidget()
            page.setObjectName("placeholderPage")
            page_layout = QVBoxLayout(page)
            page_layout.addStretch()
            label = QLabel("Раздел в разработке")
            label.setObjectName("placeholderText")
            page_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
            page_layout.addStretch()
            self.tabs.addTab(page, name)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(320)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_title = QLabel("Источник и запуск")
        sidebar_title.setObjectName("sectionTitle")
        sidebar_title.setContentsMargins(18, 18, 18, 12)
        sidebar_layout.addWidget(sidebar_title)

        self.settings_widget = SettingsWidget()
        self.settings_dialog = QDialog(self)
        self.settings_dialog.setWindowTitle("Настройки анализа")
        self.settings_dialog.setObjectName("settingsDialog")
        self.settings_dialog.setMinimumWidth(390)
        dialog_layout = QVBoxLayout(self.settings_dialog)
        dialog_layout.setContentsMargins(20, 16, 20, 20)
        dialog_layout.setSpacing(12)
        dialog_layout.addWidget(self.settings_widget.params_group)
        dialog_layout.addWidget(self.settings_widget.display_group)
        close_settings = QPushButton("Готово")
        close_settings.clicked.connect(self.settings_dialog.close)
        dialog_layout.addWidget(close_settings)
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

    def _show_settings(self):
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    # === Предпросмотр видео ===
    def _selected_source(self):
        source = self.settings_widget._get_selected_source()
        source_type = self.settings_widget.source_type_combo.currentData()
        if source_type == "file":
            return source, f"file:{Path(source).expanduser().resolve()}"
        return source, f"{source_type}:{source}"

    def _on_tab_changed(self, index: int):
        if index == 1:
            try:
                _, key = self._selected_source()
            except ValueError:
                key = None
            if key == self.zones_widget.source and self.zones_widget.canvas.frame is not None:
                return
            self._load_zone_frame()

    def _load_zone_frame(self):
        try:
            source, key = self._selected_source()
        except ValueError as error:
            self.zones_widget.clear_context(str(error))
            return

        frame = None
        if self.settings_widget.source_type_combo.currentData() == "file":
            capture = cv2.VideoCapture(str(source))
            try:
                if capture.isOpened():
                    capture.set(cv2.CAP_PROP_POS_FRAMES, self.settings_widget.seek_slider.value())
                    success, frame = capture.read()
                    if not success:
                        frame = None
            finally:
                capture.release()
        elif self._display_source_key == key and self.video_widget.last_frame is not None:
            frame = self.video_widget.last_frame

        if frame is None:
            self.zones_widget.clear_context(
                "Не удалось получить кадр. Для камеры или RTSP сначала запустите анализ."
            )
            return
        self.zones_widget.set_context(key, frame)

    def _on_zones_changed(self):
        if self._display_source_key == self.zones_widget.source:
            self.video_widget.set_zones(self.zones_widget.manager.get_zones())
            self._zones_loaded_for = (*self.zones_widget.frame_size, self._display_source_key)

    def _show_frame(self, frame):
        height, width = frame.shape[:2]
        identity = (width, height, self._display_source_key)
        if self._zones_loaded_for != identity:
            try:
                manager = self.zones_widget.store.load(self._display_source_key, width, height)
                self.video_widget.set_zones(manager.get_zones())
            except (OSError, ValueError, KeyError, TypeError):
                self.video_widget.set_zones([])
            self._zones_loaded_for = identity
        self.video_widget.update_frame(frame)

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

        _, self._display_source_key = self._selected_source()
        self._zones_loaded_for = None

        if self.preview_thread is not None and self.preview_thread.isRunning():
            playing = self.preview_thread.toggle_playback()
            self.settings_widget.set_preview_playing(playing)
            return

        start_frame = self.settings_widget.seek_slider.value()
        total_frames = self.settings_widget._total_frames

        if total_frames > 0 and start_frame >= total_frames - 1:
            start_frame = 0

        self.preview_thread = VideoPreviewThread(source, start_frame=start_frame)

        self.preview_thread.frame_ready.connect(self._show_frame)
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
        source_type = self.settings_widget.source_type_combo.currentData()
        source = sources[0]
        if source_type == "file":
            self._display_source_key = f"file:{Path(source).expanduser().resolve()}"
        else:
            self._display_source_key = f"{source_type}:{source}"
        self._zones_loaded_for = None
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

        self.thread.frame_ready.connect(self._show_frame)
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
