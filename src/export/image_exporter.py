"""Export a saved heatmap or overlay as a PNG image."""

from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import QImage

from src.export import save_bytes


def read_image(source: Path) -> QImage:
    image = QImage.fromData(source.read_bytes())
    if image.isNull():
        raise ValueError(f"Не удалось прочитать изображение {source.name}.")
    return image


def export_png(source: Path, destination: Path) -> None:
    image = read_image(source)
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise OSError("Не удалось сформировать PNG.")
    save_bytes(destination, bytes(buffer.data()))
