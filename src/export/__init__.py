"""File export helpers."""

from pathlib import Path

from PyQt6.QtCore import QIODevice, QSaveFile


def save_bytes(destination: Path, payload: bytes) -> None:
    """Replace the destination only after writing the complete file."""
    file = QSaveFile(str(destination))
    if not file.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(file.errorString())
    if file.write(payload) != len(payload):
        file.cancelWriting()
        raise OSError(file.errorString())
    if not file.commit():
        raise OSError(file.errorString())
