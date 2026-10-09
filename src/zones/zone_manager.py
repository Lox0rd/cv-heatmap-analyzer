
from dataclasses import dataclass

import cv2
import numpy as np


Point = tuple[int, int]


@dataclass(frozen=True)
class Zone:
    """Зона интереса в виде многоугольника."""

    name: str
    points: tuple[Point, ...]


class ZoneManager:
    """Создание и проверка зон интереса на кадре."""

    def __init__(self):
        self._zones: dict[str, Zone] = {}

    def add_zone(self, name: str, points: list[Point]) -> Zone:
        """Добавляет зону по координатам вершин."""

        name = name.strip()

        if not name:
            raise ValueError("Название зоны не может быть пустым")

        if name in self._zones:
            raise ValueError(f"Зона '{name}' уже существует")

        if len(points) < 3:
            raise ValueError(
                "Для создания зоны необходимо минимум 3 точки"
            )

        normalized_points = []

        for point in points:
            if (
                not isinstance(point, (tuple, list))
                or len(point) != 2
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, np.integer))
                    for value in point
                )
            ):
                raise ValueError(
                    "Координаты должны быть целочисленными парами (x, y)"
                )

            normalized_points.append(
                (int(point[0]), int(point[1]))
            )

        if len(set(normalized_points)) < 3:
            raise ValueError(
                "Зона должна содержать минимум 3 различные точки"
            )

        contour = np.array(
            normalized_points,
            dtype=np.int32
        ).reshape((-1, 1, 2))

        if cv2.contourArea(contour) == 0:
            raise ValueError(
                "Нельзя создать зону с нулевой площадью"
            )

        zone = Zone(
            name=name,
            points=tuple(normalized_points)
        )

        self._zones[name] = zone

        return zone

    def remove_zone(self, name: str) -> None:
        """Удаляет зону по названию."""

        if name not in self._zones:
            raise KeyError(f"Зона '{name}' не найдена")

        del self._zones[name]

    def get_zone(self, name: str) -> Zone:
        """Возвращает одну зону по названию."""

        if name not in self._zones:
            raise KeyError(f"Зона '{name}' не найдена")

        return self._zones[name]

    def get_zones(self) -> list[Zone]:
        """Возвращает список всех зон."""

        return list(self._zones.values())

    def is_point_in_zone(
        self,
        point: Point,
        zone_name: str
    ) -> bool:
        """Проверяет, находится ли точка внутри зоны."""

        zone = self.get_zone(zone_name)

        contour = np.array(
            zone.points,
            dtype=np.int32
        ).reshape((-1, 1, 2))

        result = cv2.pointPolygonTest(
            contour,
            (float(point[0]), float(point[1])),
            False
        )

        # Точка на границе тоже считается частью зоны.
        return result >= 0

    def find_zones(self, point: Point) -> list[str]:
        """Возвращает названия зон, содержащих точку."""

        return [
            zone.name
            for zone in self.get_zones()
            if self.is_point_in_zone(point, zone.name)
        ]
