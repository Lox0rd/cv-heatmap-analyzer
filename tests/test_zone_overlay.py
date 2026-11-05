import numpy as np

from src.zones.overlay import draw_zones
from src.zones.zone_manager import Zone


def test_draw_zones_marks_frame_without_changing_source():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    zone = Zone("Вход", ((20, 20), (80, 20), (80, 80), (20, 80)))

    result = draw_zones(frame, [zone])

    assert np.count_nonzero(result) > 0
    assert np.any(result[20, 50] != 0)
    assert np.count_nonzero(frame) == 0
    assert np.count_nonzero(draw_zones(frame, [])) == 0
