import cv2
import numpy as np
import pytest

from src.heatmap.generator import HeatmapGenerator
from src.heatmap.renderer import HeatmapRenderer


# ==================== HeatmapGenerator ====================

def test_generator_initialization():
    generator = HeatmapGenerator(width=100, height=80)

    assert generator.width == 100
    assert generator.height == 80
    assert generator.heatmap.shape == (80, 100)
    assert generator.heatmap.dtype == np.float32
    assert np.all(generator.heatmap == 0)


def test_generator_update():
    generator = HeatmapGenerator(width=100, height=100)

    generator.update([
        {"bbox": (20, 20, 40, 40)},
    ])

    heatmap = generator.get_heatmap()

    # Точка интереса находится внизу по центру bbox: (30, 40).
    assert heatmap[40, 30] > 0
    assert heatmap.max() == pytest.approx(1.0)


def test_generator_multiple_detections():
    generator = HeatmapGenerator(width=100, height=100)

    generator.update([
        {"bbox": (10, 10, 30, 30)},
        {"bbox": (60, 60, 80, 80)},
    ])

    heatmap = generator.get_heatmap()

    assert heatmap[30, 20] > 0
    assert heatmap[80, 70] > 0


def test_generator_ignores_detection_outside_bounds():
    generator = HeatmapGenerator(width=100, height=100)

    generator.update([
        {"bbox": (200, 200, 220, 220)},
    ])

    assert np.all(generator.get_heatmap() == 0)


def test_generator_ignores_negative_coordinates():
    generator = HeatmapGenerator(width=100, height=100)

    generator.update([
        {"bbox": (-30, -30, -10, -10)},
    ])

    assert np.all(generator.get_heatmap() == 0)


def test_generator_ignores_point_on_right_boundary():
    generator = HeatmapGenerator(width=100, height=100)

    # x = (90 + 110) // 2 = 100, что выходит за границу.
    generator.update([
        {"bbox": (90, 90, 110, 100)},
    ])

    assert np.all(generator.get_heatmap() == 0)


def test_generator_ignores_point_on_bottom_boundary():
    generator = HeatmapGenerator(width=100, height=100)

    generator.update([
        {"bbox": (40, 90, 60, 100)},
    ])

    assert np.all(generator.get_heatmap() == 0)


def test_generator_empty_detections():
    generator = HeatmapGenerator(width=100, height=100)

    generator.update([])

    assert np.all(generator.get_heatmap() == 0)


def test_generator_get_heatmap_returns_internal_matrix():
    generator = HeatmapGenerator(width=50, height=50)

    heatmap = generator.get_heatmap()
    heatmap[10, 10] = 5.0

    assert generator.get_heatmap()[10, 10] == 5.0


# ==================== HeatmapRenderer ====================

def test_renderer_nonempty_heatmap():
    renderer = HeatmapRenderer()

    heatmap = np.zeros((100, 100), dtype=np.float32)
    heatmap[50, 50] = 1.0

    result = renderer.render(heatmap)

    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8
    assert np.any(result != 0)


def test_renderer_normalizes_heatmap():
    renderer = HeatmapRenderer()

    heatmap = np.zeros((50, 50), dtype=np.float32)
    heatmap[25, 25] = 10.0

    result = renderer.render(heatmap)

    assert result.dtype == np.uint8
    assert result.shape == (50, 50, 3)
    assert result.max() > 0


def test_renderer_overlay():
    renderer = HeatmapRenderer()

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    heatmap = np.zeros((100, 100), dtype=np.float32)
    heatmap[50, 50] = 1.0

    result = renderer.overlay(frame, heatmap)

    assert result.shape == frame.shape
    assert result.dtype == np.uint8
    assert np.any(result != 0)


def test_renderer_overlay_custom_alpha():
    renderer = HeatmapRenderer()

    frame = np.full((50, 50, 3), 100, dtype=np.uint8)
    heatmap = np.zeros((50, 50), dtype=np.float32)
    heatmap[25, 25] = 1.0

    result = renderer.overlay(frame, heatmap, alpha=0.25)

    assert result.shape == frame.shape
    assert result.dtype == np.uint8


def test_renderer_save_success(tmp_path):
    renderer = HeatmapRenderer()

    heatmap = np.zeros((100, 100), dtype=np.float32)
    heatmap[50, 50] = 1.0

    output_path = str(tmp_path / "heatmap.png")

    renderer.save(heatmap, output_path)

    assert (tmp_path / "heatmap.png").exists()

    saved_image = cv2.imread(output_path)

    assert saved_image is not None
    assert saved_image.shape == (100, 100, 3)


def test_renderer_save_failure(monkeypatch, tmp_path):
    renderer = HeatmapRenderer()

    heatmap = np.zeros((100, 100), dtype=np.float32)
    output_path = str(tmp_path / "heatmap.png")

    monkeypatch.setattr(
        "src.heatmap.renderer.cv2.imwrite",
        lambda *args, **kwargs: False,
    )

    with pytest.raises(
        IOError,
        match="Не удалось сохранить тепловую карту",
    ):
        renderer.save(heatmap, output_path)
