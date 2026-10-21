
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QDoubleSpinBox,
    QSpinBox,
    QFileDialog,
    QSlider,
    QCheckBox,
)
from PyQt6.QtCore import pyqtSignal, Qt


class SettingsWidget(QWidget):
    start_requested = pyqtSignal(
        list, float, float, int, str, bool, bool
    )
    stop_requested = pyqtSignal()
    seek_requested = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Источник видео.
        source_group = QGroupBox("Источник видео")
        source_layout = QVBoxLayout()

        self.source_input = QLineEdit(
            "data/input/VideoTests/cars1.mp4"
        )
        source_layout.addWidget(self.source_input)

        btn_layout = QHBoxLayout()

        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self.browse_file)
        btn_layout.addWidget(browse_btn)

        source_layout.addLayout(btn_layout)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # Ползунок перемотки видео.
        self.seek_group = QGroupBox("Прокрутка видео")
        seek_layout = QVBoxLayout()

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setEnabled(False)
        self.seek_slider.valueChanged.connect(
            self._on_seek_changed
        )

        self.seek_label = QLabel("Кадр: 0 / 0")
        self.seek_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        seek_layout.addWidget(self.seek_slider)
        seek_layout.addWidget(self.seek_label)

        self.seek_group.setLayout(seek_layout)
        layout.addWidget(self.seek_group)

        self._total_frames = 0

        # Параметры обработки.
        params_group = QGroupBox("Параметры")
        params_layout = QVBoxLayout()

        self.conf_spin = self._add_spin(
            params_layout,
            "Confidence:",
            0.1,
            1.0,
            0.5,
            0.05,
        )

        self.alpha_spin = self._add_spin(
            params_layout,
            "Alpha (наложение):",
            0.1,
            1.0,
            0.5,
            0.1,
        )

        self.skip_spin = self._add_int_spin(
            params_layout,
            "Пропуск кадров:",
            0,
            10,
            0,
            1,
        )

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Настройки отображения.
        display_group = QGroupBox("Отображение")
        display_layout = QVBoxLayout()

        self.cb_detections = QCheckBox(
            "Показывать детекцию"
        )
        self.cb_detections.setChecked(True)
        display_layout.addWidget(self.cb_detections)

        self.cb_heatmap = QCheckBox(
            "Показывать тепловую карту"
        )
        self.cb_heatmap.setChecked(True)
        display_layout.addWidget(self.cb_heatmap)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Кнопки управления.
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("Старт")
        self.start_btn.clicked.connect(self._on_start)

        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        layout.addLayout(control_layout)

        # Статус обработки.
        self.status_label = QLabel("Готов к работе")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        layout.addStretch()

    # Вспомогательные методы.
    def _add_spin(
        self,
        parent_layout,
        text,
        min_val,
        max_val,
        default,
        step,
    ):
        row = QHBoxLayout()

        row.addWidget(QLabel(text))

        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)

        row.addWidget(spin)
        parent_layout.addLayout(row)

        return spin

    def _add_int_spin(
        self,
        parent_layout,
        text,
        min_val,
        max_val,
        default,
        step,
    ):
        row = QHBoxLayout()

        row.addWidget(QLabel(text))

        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)

        row.addWidget(spin)
        parent_layout.addLayout(row)

        return spin

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видео",
            "",
            "Video Files (*.mp4 *.avi *.mov)",
        )

        if file_path:
            self.source_input.setText(file_path)

    # Обработчик ползунка.
    def _on_seek_changed(self, value):
        self.seek_label.setText(
            f"Кадр: {value} / {self._total_frames}"
        )
        self.seek_requested.emit(value)

    # Методы взаимодействия с главным окном.
    def set_total_frames(self, total: int):
        self._total_frames = total
        self.seek_slider.setRange(0, max(0, total - 1))
        self.seek_label.setText(f"Кадр: 0 / {total}")

    def set_current_frame(self, frame_index: int):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(frame_index)
        self.seek_slider.blockSignals(False)

        self.seek_label.setText(
            f"Кадр: {frame_index} / {self._total_frames}"
        )

    def set_seek_enabled(self, enabled: bool):
        self.seek_slider.setEnabled(enabled)

        if not enabled:
            self.seek_slider.setRange(0, 0)
            self.seek_label.setText("Недоступно для потоков")

    # Запуск и остановка обработки.
    def _on_start(self):
        sources = [self.source_input.text().strip()]

        self.start_requested.emit(
            sources,
            self.conf_spin.value(),
            self.alpha_spin.value(),
            self.skip_spin.value(),
            "Jet",
            self.cb_detections.isChecked(),
            self.cb_heatmap.isChecked(),
        )

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.source_input.setEnabled(False)

    def _on_stop(self):
        self.stop_requested.emit()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.source_input.setEnabled(True)

    def set_status(self, text: str):
        self.status_label.setText(text)
