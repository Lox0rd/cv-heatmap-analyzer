# src/gui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
)

from src.gui.video_widget import VideoWidget
from src.gui.settings_widget import SettingsWidget
from src.gui.processing_thread import ProcessingThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CV Heatmap Analyzer")
        self.resize(1200, 700)

        self.thread = None
        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)

        self.video_widget = VideoWidget()
        left_layout.addWidget(
            self.video_widget,
            stretch=1
        )

        self.settings_widget = SettingsWidget()

        # Переносим ползунок из правой панели под видео
        left_layout.addWidget(
            self.settings_widget.seek_group,
            stretch=0
        )

        main_layout.addLayout(
            left_layout,
            stretch=3
        )
        main_layout.addWidget(
            self.settings_widget,
            stretch=1
        )

        # Подключение сигналов
        self.settings_widget.start_requested.connect(self.start_processing)
        self.settings_widget.stop_requested.connect(self.stop_processing)
        self.settings_widget.seek_requested.connect(self._on_seek)

        self.setStyleSheet("""
            /* Белый цвет текста для основных элементов */
            QLabel, QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QGroupBox {
                color: #ffffff;
            }

            /* Темный фон для полей ввода, чтобы белый текст был виден */
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
            }

            /* Белый цвет заголовков групп (Источник, Параметры и т.д.) */
            QGroupBox::title {
                color: #ffffff;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }

            /* Выпадающий список (чтобы стрелочка и фон были нормальными) */
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
        """)

        central_widget.setStyleSheet("background-color: #181A1F;")  # Темно-серый фон

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
        )

        self.thread.frame_ready.connect(self.video_widget.update_frame)
        self.thread.status_update.connect(self.settings_widget.set_status)
        self.thread.frame_position_changed.connect(
            self.settings_widget.set_current_frame
        )
        self.thread.total_frames_changed.connect(
            self.settings_widget.set_total_frames
        )
        self.thread.is_file_source.connect(self.settings_widget.set_seek_enabled)
        self.thread.finished.connect(self.on_finished)

        self.thread.start()

    def _on_seek(self, frame_index: int):
        """Перемотка видео."""
        if self.thread and self.thread.isRunning():
            print(f"[MainWindow] Seek to frame {frame_index}")
            self.thread.seek(frame_index)

    def stop_processing(self):
        if self.thread and self.thread.isRunning():
            self.settings_widget.set_status("Остановка...")
            self.thread.stop()

    def on_finished(self):
        self.settings_widget.set_status(
            "Готово. Тепловая карта сохранена в data/output/"
        )
        self.settings_widget.start_btn.setEnabled(True)
        self.settings_widget.stop_btn.setEnabled(False)
        self.settings_widget.source_input.setEnabled(True)

    def closeEvent(self, event):
        self.stop_processing()
        event.accept()