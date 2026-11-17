import csv
import json

from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QFileDialog

from src.analysis.zone_statistics import ZoneStatistics
from src.gui.export_widget import ExportWidget
from src.zones.zone_manager import Zone


def test_export_tab_writes_saved_results(qtbot, monkeypatch, tmp_path):
    raw = tmp_path / "heatmap_raw.jpg"
    overlay = tmp_path / "heatmap_overlay.jpg"
    image = QImage(120, 80, QImage.Format.Format_RGB32)
    image.fill(QColor("steelblue"))
    assert image.save(str(raw))
    assert image.save(str(overlay))

    statistics = tmp_path / "zone_statistics.json"
    zone = Zone("=Касса", ((0, 0), (50, 0), (50, 50)))
    data = ZoneStatistics([zone], 25, "rtsp:rtsp://operator:secret@example.test/live")
    data.add_frame(25, [{"label": "person", "track_id": 1, "bbox": (3, 0, 5, 1)}])
    data.save(statistics)

    widget = ExportWidget(lambda path: ("Активность возле кассы.", image))
    qtbot.addWidget(widget)
    assert all(not button.isEnabled() for button, _ in widget._actions)
    widget.refresh(tmp_path, statistics)
    widget.begin_processing()
    assert all(not button.isEnabled() for button, _ in widget._actions)
    widget.refresh(tmp_path, statistics)

    destinations = [
        tmp_path / filename
        for filename in (
            "report.pdf",
            "zones.csv",
            "timeline.csv",
            "statistics.json",
            "map.png",
            "overlay.png",
        )
    ]
    for (button, _), destination in zip(widget._actions, destinations, strict=True):
        monkeypatch.setattr(QFileDialog, "exec", lambda dialog: 1)
        monkeypatch.setattr(
            QFileDialog, "selectedFiles", lambda dialog: [str(destination)]
        )
        assert button.isEnabled()
        button.click()
        assert widget.status_label.text() == f"Сохранено: {destination}"

    report, zones, timeline, structured, map_image, overlay_image = destinations
    assert report.read_bytes().startswith(b"%PDF-")
    with zones.open(encoding="utf-8-sig", newline="") as stream:
        assert list(csv.reader(stream))[1] == ["'=Касса", "1", "0", "1"]
    with timeline.open(encoding="utf-8-sig", newline="") as stream:
        assert list(csv.reader(stream))[1] == ["1", "1", "1", "0"]
    result = json.loads(structured.read_text(encoding="utf-8"))
    assert "source_key" not in result
    assert result["zones"][0]["name"] == "=Касса"
    for path in (map_image, overlay_image):
        assert QImage(str(path)).size() == image.size()

    json_button = widget._actions[3][0]
    monkeypatch.setattr(QFileDialog, "selectedFiles", lambda dialog: [str(statistics)])
    original = statistics.read_bytes()
    json_button.click()
    assert "Выберите другое имя" in widget.status_label.text()
    assert statistics.read_bytes() == original


def test_new_overlay_disables_exports_for_previous_run(qtbot, tmp_path):
    raw = tmp_path / "heatmap_raw.jpg"
    overlay = tmp_path / "heatmap_overlay.jpg"
    stats = tmp_path / "zone_statistics.json"
    for path in (raw, overlay, stats):
        path.touch()
    metadata = tmp_path / "heatmap_overlay.source.json"
    metadata.write_text(
        '{"raw_available": false, "statistics_available": false}',
        encoding="utf-8",
    )

    widget = ExportWidget(lambda path: None)
    qtbot.addWidget(widget)
    widget.refresh(tmp_path, stats)
    assert [button.isEnabled() for button, _ in widget._actions] == [
        True,
        False,
        False,
        False,
        False,
        True,
    ]
