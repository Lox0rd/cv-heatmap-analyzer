import numpy as np
from PyQt6.QtCore import QPoint, QPointF, Qt

from src.gui.zones_widget import ZonesWidget
from src.zones.zone_store import ZoneStore


def test_draw_save_and_reload_zone(qtbot, tmp_path):
    store = ZoneStore(tmp_path / "zones.json")
    widget = ZonesWidget(store)
    qtbot.addWidget(widget)
    widget.resize(1000, 700)
    widget.show()
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    widget.set_context("file:sample.mp4", frame)
    widget.name_input.setText("Вход")
    widget.begin_zone()

    rect = widget.canvas.image_rect()
    for x, y in ((20, 20), (160, 20), (160, 80)):
        point = QPoint(
            round(rect.left() + x * rect.width() / 200),
            round(rect.top() + y * rect.height() / 100),
        )
        qtbot.mouseClick(widget.canvas, Qt.MouseButton.LeftButton, pos=point)

    assert widget.save_btn.isEnabled()
    widget.save_zone()
    assert widget.zone_list.count() == 1
    for actual, expected in zip(
        widget.manager.get_zone("Вход").points,
        ((20, 20), (160, 20), (160, 80)),
    ):
        assert abs(actual[0] - expected[0]) <= 1
        assert abs(actual[1] - expected[1]) <= 1
    assert len(store.load("file:sample.mp4", 200, 100).get_zones()) == 1

    widget.zone_list.setCurrentRow(0)
    widget.delete_zone()
    assert store.load("file:sample.mp4", 200, 100).get_zones() == []


def test_canvas_ignores_letterbox_clicks(qtbot, tmp_path):
    widget = ZonesWidget(ZoneStore(tmp_path / "zones.json"))
    qtbot.addWidget(widget)
    widget.resize(1000, 700)
    widget.show()
    widget.set_context("source", np.zeros((100, 200, 3), dtype=np.uint8))
    widget.begin_zone()

    assert widget.canvas.frame_point(QPointF(1, 1)) is None
    assert widget.canvas.draft == []
