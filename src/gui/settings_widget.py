
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import (
    DEFAULT_CAMERA_INDEX,
    DEFAULT_SKIP_FRAMES,
    DEFAULT_VIDEO_SOURCE,
    DETECTED_OBJECTS,
    DETECTION_CONFIDENCE,
    HEATMAP_ALPHA,
    HEATMAP_COLORMAP_NAME,
)


class CheckableComboBox(QComboBox):
    """Combo box that lets users choose more than one object class."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.view().pressed.connect(self._toggle_item)
        self.activated.connect(self._reopen_after_selection)

    def add_checkable_item(self, label, value, checked=True):
        self.addItem(label, value)
        item = self.model().item(self.count() - 1)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        self._refresh_text()

    def _toggle_item(self, index):
        item = self.model().itemFromIndex(index)
        state = item.checkState()
        item.setCheckState(
            Qt.CheckState.Unchecked
            if state == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        self._refresh_text()

    def _reopen_after_selection(self, _index):
        QTimer.singleShot(0, self._refresh_and_reopen)

    def _refresh_and_reopen(self):
        self._refresh_text()
        self.showPopup()

    def _refresh_text(self):
        checked_labels = [
            self.itemText(index)
            for index in range(self.count())
            if self.model().item(index).checkState() == Qt.CheckState.Checked
        ]
        self.setEditText(", ".join(checked_labels) or "Ничего не выбрано")

    def selected_values(self):
        return [
            self.itemData(index)
            for index in range(self.count())
            if self.model().item(index).checkState() == Qt.CheckState.Checked
        ]


class SettingsWidget(QWidget):
    start_requested = pyqtSignal(
        list, float, float, int, str, bool, bool, list
    )
    stop_requested = pyqtSignal()
    seek_requested = pyqtSignal(int)
    preview_play_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # === Источник видео ===
        source_group = QGroupBox("Источник видео")
        source_layout = QVBoxLayout()

        self.source_type_combo = QComboBox()
        self.source_type_combo.addItem(
            "Видео из файла", "file"
        )
        self.source_type_combo.addItem(
            "RTSP-камера", "rtsp"
        )
        self.source_type_combo.addItem(
            "Веб-камера", "camera"
        )

        source_layout.addWidget(QLabel("Тип источника:"))
        source_layout.addWidget(self.source_type_combo)

        # === Выбор видеофайла ===
        self.file_widget = QWidget()
        file_layout = QVBoxLayout(self.file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)

        file_row = QHBoxLayout()

        self.source_input = QLineEdit(
            DEFAULT_VIDEO_SOURCE
        )
        self.source_input.setPlaceholderText(
            "Путь к видеофайлу"
        )

        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.clicked.connect(self.browse_file)

        file_row.addWidget(self.source_input, stretch=1)
        file_row.addWidget(self.browse_btn)

        file_layout.addLayout(file_row)
        source_layout.addWidget(self.file_widget)

        # === RTSP-камера ===
        self.rtsp_widget = QWidget()
        rtsp_layout = QVBoxLayout(self.rtsp_widget)
        rtsp_layout.setContentsMargins(0, 0, 0, 0)

        rtsp_layout.addWidget(
            QLabel("Адрес RTSP-потока:")
        )

        self.rtsp_input = QLineEdit()
        self.rtsp_input.setPlaceholderText(
            "rtsp://192.168.1.100:554/stream"
        )

        rtsp_layout.addWidget(self.rtsp_input)
        source_layout.addWidget(self.rtsp_widget)

        # === Веб-камера ===
        self.camera_widget = QWidget()
        camera_layout = QVBoxLayout(self.camera_widget)
        camera_layout.setContentsMargins(0, 0, 0, 0)

        camera_layout.addWidget(
            QLabel("Индекс веб-камеры:")
        )

        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 20)
        self.camera_index.setValue(DEFAULT_CAMERA_INDEX)
        self.camera_index.setToolTip(
            "0 — камера по умолчанию, "
            "1 — следующая камера и т. д."
        )

        camera_layout.addWidget(self.camera_index)
        source_layout.addWidget(self.camera_widget)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        self.source_type_combo.currentIndexChanged.connect(
            self._on_source_type_changed
        )

        # === Предпросмотр и перемотка ===
        self.seek_group = QGroupBox("Предпросмотр видео")
        seek_layout = QVBoxLayout()

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(
            self.preview_play_requested.emit
        )

        self.seek_slider = QSlider(
            Qt.Orientation.Horizontal
        )
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setEnabled(False)
        self.seek_slider.valueChanged.connect(
            self._on_seek_changed
        )

        self.seek_label = QLabel("Кадр: 0 / 0")
        self.seek_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        seek_controls = QHBoxLayout()
        seek_controls.addWidget(self.play_btn)
        seek_controls.addWidget(
            self.seek_slider, stretch=1
        )

        seek_layout.addLayout(seek_controls)
        seek_layout.addWidget(self.seek_label)

        self.seek_group.setLayout(seek_layout)
        layout.addWidget(self.seek_group)

        self._total_frames = 0
        self._analysis_running = False
        self._on_source_type_changed()

        # === Параметры обработки ===
        params_group = QGroupBox("Параметры")
        params_layout = QVBoxLayout()

        self.conf_spin = self._add_spin(
            params_layout,
            "Уверенность:",
            0.1,
            1.0,
            DETECTION_CONFIDENCE,
            0.05,
        )

        self.alpha_spin = self._add_spin(
            params_layout,
            "Наложение:",
            0.1,
            1.0,
            HEATMAP_ALPHA,
            0.1,
        )

        self.skip_spin = self._add_int_spin(
            params_layout,
            "Пропуск кадров:",
            0,
            10,
            DEFAULT_SKIP_FRAMES,
            1,
        )

        self.object_combo = CheckableComboBox()
        object_labels = {
            "person": "Человек",
            "bicycle": "Велосипед",
            "car": "Автомобиль",
            "motorcycle": "Мотоцикл",
            "bus": "Автобус",
            "truck": "Грузовик",
        }
        for object_name in DETECTED_OBJECTS:
            self.object_combo.add_checkable_item(
                object_labels.get(object_name, object_name),
                object_name,
            )
        params_layout.addWidget(QLabel("Объекты для детекции:"))
        params_layout.addWidget(self.object_combo)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # === Настройки отображения ===
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

        # === Кнопки управления анализом ===
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

        # === Статус ===
        self.status_label = QLabel("Готов к работе")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch()

    # === Переключение типа источника ===
    def _on_source_type_changed(self, index=None):
        source_type = self.source_type_combo.currentData()

        is_file = source_type == "file"

        self.file_widget.setVisible(is_file)
        self.seek_group.setVisible(
            is_file and not self._analysis_running
        )
        self.rtsp_widget.setVisible(source_type == "rtsp")
        self.camera_widget.setVisible(
            source_type == "camera"
        )

        self.play_btn.setEnabled(is_file)

        self.seek_slider.setEnabled(
            is_file and self._total_frames > 0
        )

        if not is_file:
            self.seek_label.setText(
                "Недоступно для потоков"
            )
        else:
            self.seek_label.setText(
                f"Кадр: {self.seek_slider.value()} "
                f"/ {self._total_frames}"
            )

    def _get_selected_source(self):
        """Возвращает источник для VideoProcessor."""
        source_type = self.source_type_combo.currentData()

        if source_type == "file":
            source = self.source_input.text().strip()

            if not source:
                raise ValueError("Выберите видеофайл.")

            return source

        if source_type == "rtsp":
            source = self.rtsp_input.text().strip()

            if not source:
                raise ValueError(
                    "Введите адрес RTSP-камеры."
                )

            if not source.lower().startswith(
                ("rtsp://", "rtsps://")
            ):
                raise ValueError(
                    "Адрес RTSP должен начинаться "
                    "с rtsp:// или rtsps://."
                )

            return source

        if source_type == "camera":
            return self.camera_index.value()

        raise ValueError("Неизвестный тип источника.")

    # === Работа с файлами ===
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видео",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm);;"
            "All Files (*)",
        )

        if file_path:
            self.source_input.setText(file_path)
            self._total_frames = 0
            self.seek_slider.setRange(0, 0)
            self.seek_label.setText("Кадр: 0 / 0")
            self.seek_slider.setEnabled(False)

    # === Создание параметров ===
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

    # === Перемотка ===
    def _on_seek_changed(self, value):
        self.seek_label.setText(
            f"Кадр: {value} / {self._total_frames}"
        )
        self.seek_requested.emit(value)

    def set_total_frames(self, total: int):
        self._total_frames = max(0, total)

        self.seek_slider.setRange(
            0, max(0, self._total_frames - 1)
        )

        self.seek_label.setText(
            f"Кадр: {self.seek_slider.value()} "
            f"/ {self._total_frames}"
        )

        self._on_source_type_changed()

    def set_current_frame(self, frame_index: int):
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(frame_index)
        self.seek_slider.blockSignals(False)

        self.seek_label.setText(
            f"Кадр: {frame_index} / {self._total_frames}"
        )

    def set_seek_enabled(self, enabled: bool):
        is_file = (
            self.source_type_combo.currentData() == "file"
        )

        self.seek_slider.setEnabled(
            enabled and is_file and self._total_frames > 0
        )

        if not is_file:
            self.seek_label.setText(
                "Недоступно для потоков"
            )

    def set_analysis_running(self, running: bool):
        self._analysis_running = running
        self.seek_group.setVisible(
            not running
            and self.source_type_combo.currentData() == "file"
        )

    def set_preview_playing(self, playing: bool):
        self.play_btn.setText(
            "Ⅱ Пауза" if playing else "▶ Play"
        )

    # === Запуск и остановка анализа ===
    def _on_start(self):
        try:
            source = self._get_selected_source()
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Источник видео",
                str(error),
            )
            return

        self.start_requested.emit(
            [source],
            self.conf_spin.value(),
            self.alpha_spin.value(),
            self.skip_spin.value(),
            HEATMAP_COLORMAP_NAME,
            self.cb_detections.isChecked(),
            self.cb_heatmap.isChecked(),
            self.object_combo.selected_values(),
        )

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.play_btn.setEnabled(False)

        self._set_source_controls_enabled(False)

    def _on_stop(self):
        self.stop_requested.emit()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.play_btn.setEnabled(
            self.source_type_combo.currentData() == "file"
        )

        self._set_source_controls_enabled(True)

    def _set_source_controls_enabled(self, enabled: bool):
        self.source_type_combo.setEnabled(enabled)
        self.source_input.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.rtsp_input.setEnabled(enabled)
        self.camera_index.setEnabled(enabled)

    def set_status(self, text: str):
        self.status_label.setText(text)
