import cv2
import numpy as np

from src.gui.map_widget import MapWidget


def test_map_displays_saved_heatmap_and_overlay(qtbot, tmp_path):
    image = np.full((24, 32, 3), 120, dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "heatmap_raw.jpg"), image)
    cv2.imwrite(str(tmp_path / "heatmap_overlay.jpg"), image)
    widget = MapWidget(tmp_path)
    qtbot.addWidget(widget)

    assert widget.refresh()
    assert widget.raw_display.last_heatmap.shape == (24, 32, 3)
    assert widget.overlay_display.last_heatmap.shape == (24, 32, 3)
    assert "последнего анализа" in widget.status_label.text()

    widget.raw_display.set_placeholder("Ожидание")
    widget.refresh_btn.click()
    assert widget.raw_display.last_heatmap is not None


def test_map_reports_missing_results(qtbot, tmp_path):
    widget = MapWidget(tmp_path)
    qtbot.addWidget(widget)

    assert not widget.refresh()
    assert widget.raw_display.last_heatmap is None
    assert widget.overlay_display.last_heatmap is None
    assert "Нет результатов" in widget.status_label.text()
