import pytest

from src.zones.zone_manager import ZoneManager


@pytest.fixture
def manager():
    zone_manager = ZoneManager()
    zone_manager.add_zone("entrance", [(10, 10), (200, 10), (200, 150), (10, 150)])
    return zone_manager


def test_add_and_get_zone(manager):
    zone = manager.get_zone("entrance")

    assert zone.name == "entrance"
    assert len(zone.points) == 4


def test_point_inside_zone(manager):
    assert manager.is_point_in_zone((100, 100), "entrance")


def test_point_outside_zone(manager):
    assert not manager.is_point_in_zone((300, 300), "entrance")


def test_point_on_boundary(manager):
    assert manager.is_point_in_zone((10, 10), "entrance")


def test_find_zones(manager):
    assert manager.find_zones((100, 100)) == ["entrance"]
    assert manager.find_zones((300, 300)) == []


def test_duplicate_zone(manager):
    with pytest.raises(ValueError, match="уже существует"):
        manager.add_zone("entrance", [(0, 0), (10, 0), (10, 10)])


def test_zone_with_less_than_three_points(manager):
    with pytest.raises(ValueError, match="минимум 3 точки"):
        manager.add_zone("invalid", [(0, 0), (10, 10)])


def test_remove_zone(manager):
    manager.remove_zone("entrance")

    assert manager.get_zones() == []


def test_get_missing_zone(manager):
    with pytest.raises(KeyError, match="не найдена"):
        manager.get_zone("missing")
