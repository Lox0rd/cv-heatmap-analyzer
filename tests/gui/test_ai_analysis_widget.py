import cv2
import numpy as np

from src.gui.ai_analysis_widget import AIAnalysisWidget
from src.zones.zone_manager import Zone


def test_sends_overlay_frame_and_prompt_to_vision_api(qtbot, monkeypatch, tmp_path):
    image = np.full((32, 48, 3), 90, dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "heatmap_overlay.jpg"), image)
    received = []

    class FakeVisionAPI:
        def analyze_frame(self, frame, prompt):
            received.append((frame.copy(), prompt))
            return "На кадре видна зона активности."

    monkeypatch.setattr("src.gui.ai_analysis_widget.VisionAPI", FakeVisionAPI)
    widget = AIAnalysisWidget(tmp_path, prompt_provider=lambda: "Опиши тепловую карту")
    qtbot.addWidget(widget)
    assert widget.refresh_frame()
    assert not hasattr(widget, "prompt_input")
    widget.start_analysis()
    qtbot.waitUntil(lambda: widget.status_label.text() == "Анализ завершён.")
    qtbot.waitUntil(lambda: not widget.worker.isRunning())

    assert len(received) == 1
    assert np.array_equal(received[0][0], widget.overlay_frame)
    assert received[0][1] == "Опиши тепловую карту"
    assert "зона активности" in widget.result_output.toPlainText()


def test_ai_analysis_requires_heatmap_and_prompt(qtbot, tmp_path):
    prompt = ["Начальный запрос"]
    widget = AIAnalysisWidget(tmp_path, prompt_provider=lambda: prompt[0])
    qtbot.addWidget(widget)
    assert not widget.refresh_frame()
    assert not widget.analyze_btn.isEnabled()
    widget.start_analysis()
    assert "тепловую карту" in widget.status_label.text()

    image = np.zeros((10, 10, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "heatmap_overlay.jpg"), image)
    assert widget.refresh_frame()
    prompt[0] = ""
    widget.start_analysis()
    assert "Введите промпт" in widget.status_label.text()


def test_api_error_is_shown_without_freezing_interface(qtbot, monkeypatch, tmp_path):
    cv2.imwrite(
        str(tmp_path / "heatmap_overlay.jpg"),
        np.zeros((10, 10, 3), dtype=np.uint8),
    )

    class FailingVisionAPI:
        def analyze_frame(self, frame, prompt):
            raise ValueError("Не указан COMET_API_KEY")

    monkeypatch.setattr("src.gui.ai_analysis_widget.VisionAPI", FailingVisionAPI)
    widget = AIAnalysisWidget(tmp_path)
    qtbot.addWidget(widget)
    widget.refresh_frame()
    widget.start_analysis()
    qtbot.waitUntil(lambda: "COMET_API_KEY" in widget.status_label.text())
    qtbot.waitUntil(lambda: not widget.worker.isRunning())

    assert widget.analyze_btn.isEnabled()


def test_ai_receives_frame_with_zone_contour_and_zone_name(qtbot, monkeypatch, tmp_path):
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "heatmap_overlay.jpg"), image)
    zones = [
        Zone("Вход", ((10, 10), (45, 10), (45, 45), (10, 45))),
        Zone("Касса", ((55, 55), (90, 55), (90, 90), (55, 90))),
    ]
    received = []

    class FakeVisionAPI:
        def analyze_frame(self, frame, prompt):
            received.append((frame.copy(), prompt))
            return "Готово"

    monkeypatch.setattr("src.gui.ai_analysis_widget.VisionAPI", FakeVisionAPI)
    widget = AIAnalysisWidget(
        tmp_path,
        zones_provider=lambda frame: zones,
        prompt_provider=lambda: "Что происходит в зоне?",
    )
    qtbot.addWidget(widget)
    assert widget.refresh_frame()
    widget.start_analysis()
    qtbot.waitUntil(lambda: not widget.worker.isRunning())

    sent_frame, sent_prompt = received[0]
    assert np.any(sent_frame[10, 30] != 0)
    assert "1 — Вход; 2 — Касса" in sent_prompt
    assert "Что происходит в зоне?" in sent_prompt
    assert np.array_equal(sent_frame, widget.image_display.last_heatmap)
