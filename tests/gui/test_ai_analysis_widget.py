import cv2
import numpy as np

from src.gui.ai_analysis_widget import AIAnalysisWidget


def test_sends_overlay_frame_and_prompt_to_vision_api(qtbot, monkeypatch, tmp_path):
    image = np.full((32, 48, 3), 90, dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "heatmap_overlay.jpg"), image)
    received = []

    class FakeVisionAPI:
        def analyze_frame(self, frame, prompt):
            received.append((frame.copy(), prompt))
            return "На кадре видна зона активности."

    monkeypatch.setattr("src.gui.ai_analysis_widget.VisionAPI", FakeVisionAPI)
    widget = AIAnalysisWidget(tmp_path)
    qtbot.addWidget(widget)
    assert widget.refresh_frame()
    widget.prompt_input.setPlainText("Опиши тепловую карту")
    widget.start_analysis()
    qtbot.waitUntil(lambda: widget.status_label.text() == "Анализ завершён.")
    qtbot.waitUntil(lambda: not widget.worker.isRunning())

    assert len(received) == 1
    assert np.array_equal(received[0][0], widget.overlay_frame)
    assert received[0][1] == "Опиши тепловую карту"
    assert "зона активности" in widget.result_output.toPlainText()


def test_ai_analysis_requires_heatmap_and_prompt(qtbot, tmp_path):
    widget = AIAnalysisWidget(tmp_path)
    qtbot.addWidget(widget)
    assert not widget.refresh_frame()
    assert not widget.analyze_btn.isEnabled()
    widget.start_analysis()
    assert "тепловую карту" in widget.status_label.text()

    image = np.zeros((10, 10, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "heatmap_overlay.jpg"), image)
    assert widget.refresh_frame()
    widget.prompt_input.clear()
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
