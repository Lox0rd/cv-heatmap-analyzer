from src.zones.zone_manager import ZoneManager
from src.zones.zone_store import ZoneStore


def test_zones_round_trip_by_source_and_frame_size(tmp_path):
    store = ZoneStore(tmp_path / "zones.json")
    zones = ZoneManager()
    zones.add_zone("Вход", [(5, 5), (30, 5), (30, 25)])
    store.save("file:sample.mp4", 40, 30, zones.get_zones())

    assert store.load("file:sample.mp4", 40, 30).get_zones() == zones.get_zones()
    assert store.load("file:other.mp4", 40, 30).get_zones() == []
    assert store.load("file:sample.mp4", 80, 60).get_zones() == []


def test_saving_second_source_preserves_first(tmp_path):
    store = ZoneStore(tmp_path / "zones.json")
    zones = ZoneManager()
    zones.add_zone("Вход", [(5, 5), (30, 5), (30, 25)])
    store.save("first", 40, 30, zones.get_zones())
    store.save("second", 40, 30, [])

    assert len(store.load("first", 40, 30).get_zones()) == 1
