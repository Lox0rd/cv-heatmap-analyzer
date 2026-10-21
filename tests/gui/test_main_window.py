
from unittest.mock import MagicMock

import pytest

from src.gui.main_window import MainWindow


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
