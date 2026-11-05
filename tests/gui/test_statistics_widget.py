from src.analysis.zone_statistics import ZoneStatistics
from src.gui.statistics_widget import StatisticsWidget
from src.zones.zone_manager import Zone


def test_statistics_displays_table_and_charts(qtbot, tmp_path):
    zone = Zone("Вход", ((0, 0), (50, 0), (50, 50), (0, 50)))
    stats = ZoneStatistics([zone], fps=10, source_key="file:sample.mp4")
    stats.add_frame(0, [{"bbox": (60, 10, 70, 30), "track_id": 1, "label": "person"}])
    stats.add_frame(1, [{"bbox": (10, 10, 20, 30), "track_id": 1, "label": "person"}])
    path = tmp_path / "zone_statistics.json"
    stats.save(path)

    widget = StatisticsWidget(path)
    qtbot.addWidget(widget)
    widget.resize(1200, 800)
    widget.show()

    assert widget.refresh()
    assert widget.unique_value.text() == "1"
    assert widget.peak_value.text() == "1"
    assert widget.entries_value.text() == "1"
    assert widget.zones_value.text() == "1"
    assert widget.zone_table.item(0, 0).text() == "Вход"
    assert widget.zone_table.item(0, 1).text() == "1"
    assert widget.zone_table.item(0, 2).text() == "1"
    assert widget.zone_table.item(0, 3).text() == "1"
    assert not widget.timeline_chart.pixmap().isNull()
    assert not widget.zone_chart.pixmap().isNull()


def test_statistics_reports_missing_file(qtbot, tmp_path):
    widget = StatisticsWidget(tmp_path / "missing.json")
    qtbot.addWidget(widget)

    assert not widget.refresh()
    assert widget.zone_table.rowCount() == 0
    assert "после анализа" in widget.status_label.text()


def test_old_statistics_require_new_analysis(qtbot, tmp_path):
    path = tmp_path / "zone_statistics.json"
    path.write_text('{"version": 1}', encoding="utf-8")
    widget = StatisticsWidget(path)
    qtbot.addWidget(widget)

    assert not widget.refresh()
    assert "Запустите анализ повторно" in widget.status_label.text()
