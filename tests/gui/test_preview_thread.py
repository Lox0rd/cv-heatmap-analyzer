
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PyQt6.QtTest import QSignalSpy

from src.gui.preview_thread import VideoPreviewThread


@pytest.fixture
def fake_capture():
    capture = MagicMock()
    capture.isOpened.return_value = True
    capture.get.side_effect = lambda prop: {
        5: 30.0,   # CAP_PROP_FPS
        7: 10.0,   # CAP_PROP_FRAME_COUNT
    }.get(prop, 0.0)

    capture.read.side_effect = [
        (True, np.zeros((32, 32, 3), dtype=np.uint8)),
        (False, None),
    ]

    return capture


def test_thread_initializes():
    thread = VideoPreviewThread(
        "/tmp/video.mp4",
        start_frame=5,
    )

    assert thread.video_path == "/tmp/video.mp4"
    assert thread.start_frame == 5


def test_negative_start_frame_is_clamped():
    thread = VideoPreviewThread(
        "/tmp/video.mp4",
        start_frame=-10,
    )

    assert thread.start_frame == 0


def test_seek_stores_requested_frame():
    thread = VideoPreviewThread("/tmp/video.mp4")

    thread.seek(42)

    with thread._lock:
        assert thread._pending_seek == 42


def test_negative_seek_is_clamped():
    thread = VideoPreviewThread("/tmp/video.mp4")

    thread.seek(-5)

    with thread._lock:
        assert thread._pending_seek == 0


def test_toggle_playback():
    thread = VideoPreviewThread("/tmp/video.mp4")

    assert thread.toggle_playback() is False
    assert thread.toggle_playback() is True


def test_unopenable_video_emits_error(qtbot):
    thread = VideoPreviewThread("/tmp/missing.mp4")

    with patch(
        "src.gui.preview_thread.cv2.VideoCapture"
    ) as capture_factory:
        capture_factory.return_value.isOpened.return_value = False

        with qtbot.waitSignal(
            thread.error_occurred,
            timeout=2000,
        ) as signal:
            thread.start()

        thread.wait()

    assert "Не удалось открыть видео" in signal.args[0]


def test_video_emits_frame_and_frame_count(qtbot):
    thread = VideoPreviewThread("/tmp/video.mp4")

    frames = []
    totals = QSignalSpy(thread.total_frames_changed)

    thread.frame_ready.connect(frames.append)

    with patch(
        "src.gui.preview_thread.cv2.VideoCapture"
    ) as capture_factory:
        capture = capture_factory.return_value
        capture.isOpened.return_value = True
        capture.get.side_effect = lambda prop: {
            5: 30.0,
            7: 10.0,
        }.get(prop, 0.0)
        capture.read.side_effect = [
            (True, np.zeros((32, 32, 3), dtype=np.uint8)),
            (False, None),
        ]

        thread.start()
        qtbot.waitUntil(lambda: not thread.isRunning(), timeout=2000)

    assert len(totals) == 1
    assert totals[0] == [10]
    assert len(frames) == 1

def test_video_reaches_end_and_emits_finished(qtbot):
    thread = VideoPreviewThread("/tmp/video.mp4")

    with patch(
        "src.gui.preview_thread.cv2.VideoCapture"
    ) as capture_factory:
        capture = capture_factory.return_value
        capture.isOpened.return_value = True
        capture.get.side_effect = lambda prop: {
            5: 30.0,
            7: 10.0,
        }.get(prop, 0.0)
        capture.read.side_effect = [
            (True, np.zeros((32, 32, 3), dtype=np.uint8)),
            (False, None),
        ]

        with qtbot.waitSignal(
            thread.playback_finished,
            timeout=2000,
        ):
            thread.start()

        thread.wait()

    capture.release.assert_called_once()


def test_capture_exception_emits_error(qtbot):
    thread = VideoPreviewThread("/tmp/video.mp4")

    with patch(
        "src.gui.preview_thread.cv2.VideoCapture",
        side_effect=RuntimeError("test failure"),
    ):
        with qtbot.waitSignal(
            thread.error_occurred,
            timeout=2000,
        ) as signal:
            thread.start()

        thread.wait()

    assert "Ошибка предпросмотра" in signal.args[0]
