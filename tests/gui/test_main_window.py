from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest
from PyQt6.QtWidgets import QFrame

from src.gui.main_window import MainWindow
from src.zones.zone_manager import ZoneManager
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
    assert window.people_count_label.text() == "Людей в кадре: —"
    assert [window.tabs.tabText(index) for index in range(window.tabs.count())] == [
        "Анализ",
        "Зоны",
        "Карта",
        "Статистика",
        "AI анализ",
        "Экспорт",
    ]


def test_refresh_buttons_restart_analysis_of_selected_file(
    window, monkeypatch, tmp_path
):
    video = tmp_path / "sample.mp4"
    video.touch()
    window.settings_widget.source_input.setText(str(video))
    start = MagicMock()
    monkeypatch.setattr(window.settings_widget, "_on_start", start)

    window.map_widget.refresh_btn.click()
    window.statistics_widget.refresh_btn.click()

    assert start.call_count == 2
    assert "Повторный анализ" in window.map_widget.status_label.text()
    assert "Повторный анализ" in window.statistics_widget.status_label.text()


def test_refresh_buttons_report_missing_source(window, monkeypatch):
    start = MagicMock()
    monkeypatch.setattr(window.settings_widget, "_on_start", start)
    window.settings_widget.source_input.setText("missing-video.mp4")

    window.map_widget.refresh_btn.click()

    start.assert_not_called()
    assert "Видеофайл не найден" in window.map_widget.status_label.text()


def test_map_refresh_starts_processing_thread(window, monkeypatch, tmp_path):
    video = tmp_path / "sample.mp4"
    video.touch()
    window.settings_widget.source_input.setText(str(video))
    factory = MagicMock()
    monkeypatch.setattr("src.gui.main_window.ProcessingThread", factory)

    window.map_widget.refresh_btn.click()

    assert factory.call_args.kwargs["sources"] == [str(video)]
    factory.return_value.start.assert_called_once()
    assert not window.map_widget.refresh_btn.isEnabled()
    assert not window.statistics_widget.refresh_btn.isEnabled()

    window.on_finished()
    assert window.map_widget.refresh_btn.isEnabled()
    assert window.statistics_widget.refresh_btn.isEnabled()


def test_processing_options_open_in_settings_dialog(window):
    assert window.settings_widget.params_group.parentWidget() is window.settings_dialog
    assert window.settings_widget.display_group.parentWidget() is window.settings_dialog
    assert window.settings_widget.ai_group.parentWidget() is window.settings_dialog
    assert window.settings_widget.source_group.parentWidget() is window.settings_widget
    window.settings_button.click()
    assert window.settings_dialog.isVisible()
    window.settings_widget.ai_prompt_input.setPlainText("Проверь отмеченные зоны")
    assert window.ai_widget.prompt_provider() == "Проверь отмеченные зоны"
    window.settings_dialog.close()


def test_analysis_controls_are_right_of_video(window):
    window.show()
    analysis_page = window.tabs.widget(0)
    viewer = analysis_page.findChild(QFrame, "viewerPanel")
    sidebar = analysis_page.findChild(QFrame, "sidebar")

    assert viewer.geometry().right() < sidebar.geometry().left()
    assert window.settings_widget.seek_group.parentWidget() is sidebar


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


def test_ai_uses_zones_from_analyzed_source(window, tmp_path):
    store = ZoneStore(tmp_path / "zones.json")
    manager = ZoneManager()
    manager.add_zone("Вход", [(10, 10), (80, 10), (80, 60)])
    store.save("file:analyzed.mp4", 100, 100, manager.get_zones())
    window.zones_widget.store = store
    window._analysis_result_source_key = "file:analyzed.mp4"
    window.settings_widget.source_input.setText("different.mp4")

    zones = window._zones_for_ai(np.zeros((100, 100, 3), dtype=np.uint8))

    assert [zone.name for zone in zones] == ["Вход"]


def test_ai_restores_result_source_after_restart(window, tmp_path):
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    image_path = tmp_path / "heatmap_overlay.jpg"
    cv2.imwrite(str(image_path), frame)
    store = ZoneStore(tmp_path / "zones.json")
    manager = ZoneManager()
    manager.add_zone("Вход", [(10, 10), (80, 10), (80, 60)])
    store.save("file:analyzed.mp4", 100, 100, manager.get_zones())
    window.zones_widget.store = store
    window.ai_widget.output_dir = tmp_path
    window.video_widget.update_frame(frame)
    window._display_source_key = "file:analyzed.mp4"

    window._on_result_saved(str(image_path))
    window._analysis_result_source_key = None
    window.settings_widget.source_input.setText("different.mp4")

    assert [zone.name for zone in window._zones_for_ai(frame)] == ["Вход"]


def test_ai_does_not_apply_zones_to_different_frame_size(window, tmp_path):
    window.ai_widget.output_dir = tmp_path
    (tmp_path / "heatmap_overlay.source.json").write_text(
        '{"source_key": "file:analyzed.mp4", "size": [100, 100]}',
        encoding="utf-8",
    )

    assert window._zones_for_ai(np.zeros((50, 50, 3), dtype=np.uint8)) == []


def test_analysis_passes_source_and_zone_store_to_statistics(window, monkeypatch):
    factory = MagicMock()
    monkeypatch.setattr("src.gui.main_window.ProcessingThread", factory)

    window.start_processing(
        sources=["sample.mp4"],
        confidence=0.5,
        alpha=0.5,
        skip_frames=0,
        colormap_name="Jet",
        show_detections=True,
        show_heatmap=True,
    )

    options = factory.call_args.kwargs
    assert options["source_key"].endswith("sample.mp4")
    assert options["zone_store_path"] == window.zones_widget.store.path
    window._set_people_count(3)
    assert window.people_count_label.text() == "Людей в кадре: 3"


def test_play_preview_rejects_non_file_source(
    window,
):
    window.settings_widget.source_type_combo.setCurrentIndex(1)

    window.play_preview()

    assert "только для видеофайлов" in (window.settings_widget.status_label.text())


def test_play_preview_rejects_empty_path(window):
    window.settings_widget.source_input.clear()

    window.play_preview()

    assert "выберите видеофайл" in (window.settings_widget.status_label.text().lower())


def test_play_preview_rejects_running_analysis(window):
    window.thread = MagicMock()
    window.thread.isRunning.return_value = True

    window.play_preview()

    assert "во время анализа" in (window.settings_widget.status_label.text())


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
    assert "завершён" in (window.settings_widget.status_label.text())


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


def test_failed_analysis_keeps_error_status(window):
    window.settings_widget.set_status("✗ Критическая ошибка: source failed")

    window.on_finished()

    assert "source failed" in window.settings_widget.status_label.text()
