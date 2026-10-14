import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from src.video.video_processor import VideoProcessor


def test_open_video():
    processor = VideoProcessor("tests/data/test.mp4")

    assert processor.capture.isOpened()

    processor.release()

def test_open_invalid_video():
    with pytest.raises(ValueError):
        VideoProcessor("does_not_exist.mp4")

def test_get_video_info():
    processor = VideoProcessor("tests/data/test.mp4")

    info = processor.get_info()

    assert info["source"] == "video"
    assert info["width"] > 0
    assert info["height"] > 0
    assert info["fps"] > 0
    assert info["frame_count"] > 0
    assert info["duration"] > 0

    processor.release()

def test_read_frames():
    processor = VideoProcessor("tests/data/test.mp4")

    frames = list(processor.read_frames())

    assert len(frames) > 0

    processor.release()

def test_read_frames_skip():
    processor = VideoProcessor("tests/data/test.mp4")

    frames_without_skip = list(
        processor.read_frames(skip_frames=0)
    )

    processor.set_frame_position(0)

    frames_with_skip = list(
        processor.read_frames(skip_frames=1)
    )

    assert len(frames_with_skip) < len(frames_without_skip)

    processor.release()

def test_read_frames_negative_skip():
    processor = VideoProcessor("tests/data/test.mp4")

    with pytest.raises(ValueError):
        list(processor.read_frames(skip_frames=-1))

    processor.release()

def test_resize_frame():
    processor = VideoProcessor("tests/data/test.mp4")

    frame = np.zeros((100, 200, 3), dtype=np.uint8)

    resized = processor.resize_frame(
        frame,
        width=50,
        height=30
    )

    assert resized.shape == (30, 50, 3)

    processor.release()

def test_crop_frame():
    processor = VideoProcessor("tests/data/test.mp4")

    frame = np.zeros((100, 200, 3), dtype=np.uint8)

    cropped = processor.crop_frame(
        frame,
        10, 20,
        60, 70
    )

    assert cropped.shape == (50, 50, 3)

    processor.release()

def test_convert_bgr_to_gray():
    processor = VideoProcessor("tests/data/test.mp4")

    frame = np.zeros((100, 200, 3), dtype=np.uint8)

    result = processor.convert_color(
        frame,
        "BGR2GRAY"
    )

    assert result.shape == (100, 200)

    processor.release()

def test_convert_color_invalid():
    processor = VideoProcessor("tests/data/test.mp4")

    frame = np.zeros((100, 200, 3), dtype=np.uint8)

    with pytest.raises(ValueError):
        processor.convert_color(
            frame,
            "INVALID"
        )

    processor.release()


def test_detect_source_type():
    assert VideoProcessor._detect_source_type(None, 0) == "camera"
    assert (
        VideoProcessor._detect_source_type(None, "tests/data/test.mp4")
        == "file"
    )
    assert (
        VideoProcessor._detect_source_type(
            None, "rtsp://127.0.0.1:554/stream"
        )
        == "rtsp"
    )
    assert (
        VideoProcessor._detect_source_type(
            None, "http://127.0.0.1:8080/stream"
        )
        == "http_stream"
    )


def test_read_single_frame():
    processor = VideoProcessor("tests/data/test.mp4")

    try:
        frame = processor.read_single_frame()

        assert frame is not None
        assert frame.ndim == 3
    finally:
        processor.release()


def test_set_frame_position_negative():
    processor = VideoProcessor("tests/data/test.mp4")

    try:
        with pytest.raises(ValueError):
            processor.set_frame_position(-1)
    finally:
        processor.release()


def test_set_frame_position_for_camera():
    with patch(
        "src.video.video_processor.cv2.VideoCapture"
    ) as mock_capture:
        mock_capture.return_value.isOpened.return_value = True

        processor = VideoProcessor(0)

        try:
            with pytest.raises(ValueError):
                processor.set_frame_position(10)
        finally:
            processor.release()


def test_read_single_frame_failed():
    processor = VideoProcessor("tests/data/test.mp4")

    try:
        processor.capture.read = MagicMock(
            return_value=(False, None)
        )

        assert processor.read_single_frame() is None
    finally:
        processor.release()
