
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.gui.main_window import MainWindow
from src.zones.zone_store import ZoneStore


@pytest.fixture
def window(qtbot, monkeypatch):
    # Не загружаем внешние стили во время тестов.
    monkeypatch.setattr(
        MainWindow,
        "_load_styles",
        lambda self: None,
    )

    instance = MainWindow()
    qtbot.addWidget(instance)
    return instance


def test_main_window_initializes(window):
    assert window.windowTitle() == "CV Heatmap Analyzer"
    assert window.thread is None
    assert window.preview_thread is None
    assert [window.tabs.tabText(index) for index in range(window.tabs.count())] == [
        "Анализ", "Зоны", "Карта", "Статистика", "AI анализ", "Экспорт"
    ]


def test_saved_zone_appears_on_analysis_video(window, monkeypatch, tmp_path):
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    capture = MagicMock()
    capture.isOpened.return_value = True
    capture.read.return_value = (True, frame)
    monkeypatch.setattr("src.gui.main_window.cv2.VideoCapture", lambda _: capture)
    window.zones_widget.store = ZoneStore(tmp_path / "zones.json")
    window.settings_widget.source_input.setText("sample.mp4")

    window.tabs.setCurrentIndex(1)
    window.zones_widget.name_input.setText("Вход")
    window.zones_widget.begin_zone()
    for point in ((10, 10), (80, 10), (80, 60)):
        window.zones_widget._add_point(*point)
    window.zones_widget.save_zone()

    _, window._display_source_key = window._selected_source()
    window._show_frame(frame)
    assert [zone.name for zone in window.video_widget.zones] == ["Вход"]
    assert window.video_widget.last_frame is frame
    capture.release.assert_called()


def test_play_preview_rejects_non_file_source(
    window,
):
    window.settings_widget.source_type_combo.setCurrentIndex(1)

    window.play_preview()

    assert "только для видеофайлов" in (
        window.settings_widget.status_label.text()
    )


def test_play_preview_rejects_empty_path(window):
    window.settings_widget.source_input.clear()

    window.play_preview()

    assert "выберите видеофайл" in (
        window.settings_widget.status_label.text().lower()
    )


def test_play_preview_rejects_running_analysis(window):
    window.thread = MagicMock()
    window.thread.isRunning.return_value = True

    window.play_preview()

    assert "во время анализа" in (
        window.settings_widget.status_label.text()
    )


def test_seek_is_forwarded_to_preview(window):
    preview = MagicMock()
    preview.isRunning.return_value = True
    window.preview_thread = preview

    window._on_seek(42)

    preview.seek.assert_called_once_with(42)


def test_seek_is_forwarded_to_analysis(window):
    processing = MagicMock()
    processing.isRunning.return_value = True
    window.thread = processing

    window._on_seek(25)

    processing.seek.assert_called_once_with(25)


def test_preview_finished_updates_status(window):
    window._on_preview_finished()

    assert window.settings_widget.play_btn.text() == "▶ Play"
    assert "завершён" in (
        window.settings_widget.status_label.text()
    )


def test_stop_preview_clears_thread(window):
    preview = MagicMock()
    preview.isRunning.return_value = True
    window.preview_thread = preview

    window._stop_preview()

    preview.stop.assert_called_once()
    assert window.preview_thread is None
    assert window.settings_widget.play_btn.text() == "▶ Play"


def test_on_finished_enables_controls(window):
    window.settings_widget.start_btn.setEnabled(False)
    window.settings_widget.stop_btn.setEnabled(True)

    window.on_finished()

    assert window.settings_widget.start_btn.isEnabled()
    assert not window.settings_widget.stop_btn.isEnabled()
    assert window.settings_widget.play_btn.isEnabled()
