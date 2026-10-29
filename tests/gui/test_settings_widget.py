
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from src.gui.settings_widget import SettingsWidget


@pytest.fixture
def widget(qtbot):
    result = SettingsWidget()
    qtbot.addWidget(result)
    result.show()
    qtbot.wait(50)
    return result


def test_widget_initializes(widget):
    assert widget.start_btn.text() == "Старт"
    assert widget.stop_btn.text() == "Стоп"
    assert widget.play_btn.text() == "▶ Play"
    assert widget.source_type_combo.currentData() == "file"


def test_file_source_is_visible(widget):
    widget.source_type_combo.setCurrentIndex(0)

    assert widget.file_widget.isVisible()
    assert not widget.rtsp_widget.isVisible()
    assert not widget.camera_widget.isVisible()
    assert widget.play_btn.isEnabled()


def test_rtsp_source_is_visible(widget):
    widget.source_type_combo.setCurrentIndex(1)

    assert not widget.file_widget.isVisible()
    assert widget.rtsp_widget.isVisible()
    assert not widget.camera_widget.isVisible()
    assert not widget.play_btn.isEnabled()


def test_camera_source_is_visible(widget):
    widget.source_type_combo.setCurrentIndex(2)

    assert not widget.file_widget.isVisible()
    assert not widget.rtsp_widget.isVisible()
    assert widget.camera_widget.isVisible()
    assert not widget.play_btn.isEnabled()


def test_get_file_source(widget):
    widget.source_input.setText("/tmp/video.mp4")

    assert widget._get_selected_source() == "/tmp/video.mp4"


def test_get_rtsp_source(widget):
    widget.source_type_combo.setCurrentIndex(1)
    widget.rtsp_input.setText("rtsp://localhost:554/stream")

    assert (
        widget._get_selected_source()
        == "rtsp://localhost:554/stream"
    )


def test_invalid_rtsp_source_raises_error(widget):
    widget.source_type_combo.setCurrentIndex(1)
    widget.rtsp_input.setText("localhost/stream")

    with pytest.raises(ValueError, match="rtsp://"):
        widget._get_selected_source()


def test_empty_rtsp_source_raises_error(widget):
    widget.source_type_combo.setCurrentIndex(1)
    widget.rtsp_input.clear()

    with pytest.raises(ValueError, match="Введите адрес"):
        widget._get_selected_source()


def test_camera_source_returns_index(widget):
    widget.source_type_combo.setCurrentIndex(2)
    widget.camera_index.setValue(2)

    assert widget._get_selected_source() == 2


def test_empty_file_source_raises_error(widget):
    widget.source_input.clear()

    with pytest.raises(ValueError, match="Выберите видеофайл"):
        widget._get_selected_source()


def test_start_emits_processing_parameters(widget, qtbot):
    widget.source_input.setText("/tmp/video.mp4")

    with qtbot.waitSignal(widget.start_requested) as signal:
        widget.start_btn.click()

    args = signal.args

    assert args[0] == ["/tmp/video.mp4"]
    assert args[1] == pytest.approx(0.5)
    assert args[2] == pytest.approx(0.5)
    assert args[3] == 0
    assert args[4] == "Jet"
    assert args[5] is True
    assert args[6] is True
    assert args[7] == [
        "person", "bicycle", "car", "motorcycle", "bus", "truck"
    ]

    assert not widget.start_btn.isEnabled()
    assert widget.stop_btn.isEnabled()


def test_object_dropdown_returns_checked_objects(widget):
    for index in range(widget.object_combo.count()):
        widget.object_combo.model().item(index).setCheckState(
            Qt.CheckState.Unchecked
        )

    widget.object_combo.model().item(2).setCheckState(
        Qt.CheckState.Checked
    )

    assert widget.object_combo.selected_values() == ["car"]


def test_start_with_empty_source_shows_warning(
    widget, monkeypatch
):
    widget.source_input.clear()

    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: messages.append(args),
    )

    widget._on_start()

    assert messages
    assert widget.start_btn.isEnabled()
    assert not widget.stop_btn.isEnabled()


def test_stop_emits_signal(widget, qtbot):
    with qtbot.waitSignal(widget.stop_requested):
        widget.stop_btn.setEnabled(True)
        widget.stop_btn.click()

    assert widget.start_btn.isEnabled()
    assert not widget.stop_btn.isEnabled()


def test_preview_button_emits_signal(widget, qtbot):
    with qtbot.waitSignal(widget.preview_play_requested):
        widget.play_btn.click()


def test_preview_button_text_changes(widget):
    widget.set_preview_playing(True)
    assert widget.play_btn.text() == "Ⅱ Пауза"

    widget.set_preview_playing(False)
    assert widget.play_btn.text() == "▶ Play"


def test_total_frames_updates_slider(widget):
    widget.set_total_frames(120)

    assert widget._total_frames == 120
    assert widget.seek_slider.minimum() == 0
    assert widget.seek_slider.maximum() == 119
    assert widget.seek_slider.isEnabled()


def test_current_frame_updates_slider_without_seek_signal(
    widget, qtbot
):
    widget.set_total_frames(100)

    with qtbot.assertNotEmitted(widget.seek_requested):
        widget.set_current_frame(25)

    assert widget.seek_slider.value() == 25
    assert "25" in widget.seek_label.text()


def test_slider_emits_seek_signal(widget, qtbot):
    widget.set_total_frames(100)

    with qtbot.waitSignal(widget.seek_requested) as signal:
        widget.seek_slider.setValue(30)

    assert signal.args == [30]


def test_set_seek_enabled(widget):
    widget.set_total_frames(100)
    widget.set_seek_enabled(False)

    assert not widget.seek_slider.isEnabled()

    widget.set_seek_enabled(True)

    assert widget.seek_slider.isEnabled()


def test_file_source_controls_can_be_disabled(widget):
    widget._set_source_controls_enabled(False)

    assert not widget.source_type_combo.isEnabled()
    assert not widget.source_input.isEnabled()
    assert not widget.browse_btn.isEnabled()

    widget._set_source_controls_enabled(True)

    assert widget.source_type_combo.isEnabled()
    assert widget.source_input.isEnabled()
    assert widget.browse_btn.isEnabled()
