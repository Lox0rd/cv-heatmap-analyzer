from src.zones.zone_manager import ZoneManager

manager = ZoneManager()

manager.add_zone(
    "entrance",
    [(10, 10), (200, 10), (200, 150), (10, 150)]
)

manager.add_zone(
    "cashier",
    [(250, 50), (400, 50), (400, 200), (250, 200)]
)

print(manager.is_point_in_zone((100, 100), "entrance"))
# True

print(manager.is_point_in_zone((300, 100), "entrance"))
# False

print(manager.find_zones((300, 100)))
# ['cashier']

print([zone.name for zone in manager.get_zones()])
# ['entrance', 'cashier']