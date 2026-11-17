"""Build a printable report from existing video analysis results."""

from html import escape
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, QMarginsF, QSize, QSizeF, Qt, QUrl
from PyQt6.QtGui import QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from src.export import save_bytes
from src.export.image_exporter import read_image


def export_pdf(
    destination: Path,
    overlay: Path | None,
    statistics: dict | None,
    commentary: tuple[str, QImage] | None = None,
) -> None:
    if overlay is None and statistics is None:
        raise ValueError("Для отчёта нужна карта или статистика.")

    document = QTextDocument()
    document.setDefaultStyleSheet("""
        body { font: 11pt; color: #18324a; }
        h1 { font-size: 23pt; color: #104a7a; }
        h2 { font-size: 15pt; color: #104a7a; }
        p { margin: 7px 0; }
        th { background-color: #e8f4fb; }
    """)
    sections = ["<h1>Отчёт об активности</h1><p>CV Heatmap Analyzer</p>"]
    if statistics is not None:
        sections.append(_statistics_section(statistics))
    if overlay is not None:
        image = commentary[1] if commentary else read_image(overlay)
        url = QUrl("report:heatmap")
        scaled = image.scaled(
            QSize(620, 340),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        document.addResource(QTextDocument.ResourceType.ImageResource, url, scaled)
        sections.append(
            '<h2>Тепловая карта на кадре</h2><p><img src="report:heatmap"></p>'
        )
    if overlay is not None and commentary:
        paragraphs = "".join(
            f"<p>{escape(line)}</p>"
            for line in commentary[0].splitlines()
            if line.strip()
        )
        sections.append("<h2>Текстовый анализ кадра</h2>" + paragraphs)
    document.setHtml("<body>" + "".join(sections) + "</body>")

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    writer = QPdfWriter(buffer)
    writer.setTitle("Отчёт об активности")
    writer.setCreator("CV Heatmap Analyzer")
    writer.setResolution(96)
    writer.setPageLayout(
        QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(15, 15, 15, 15),
            QPageLayout.Unit.Millimeter,
        )
    )
    document.setPageSize(QSizeF(writer.pageLayout().paintRectPixels(96).size()))
    document.print(writer)
    del writer
    payload = bytes(buffer.data())
    if not payload.startswith(b"%PDF-") or not payload.rstrip().endswith(b"%%EOF"):
        raise OSError("Не удалось сформировать PDF.")
    save_bytes(destination, payload)


def _statistics_section(data: dict) -> str:
    summary = (
        f"<p>Кадров обработано: <b>{data['frames_processed']}</b>. "
        f"Посетителей по ID: <b>{data['unique_people']}</b>. "
        f"Пик людей в кадре: <b>{data['peak_people_in_frame']}</b>. "
        f"Входов в зоны: <b>{data['total_zone_entries']}</b>.</p>"
    )
    if not data["zones"]:
        return "<h2>Статистика</h2>" + summary + "<p>Зоны не заданы.</p>"
    rows = "".join(
        f"<tr><td>{escape(zone['name'])}</td><td>{zone['unique_people']}</td>"
        f"<td>{zone['entries']}</td><td>{zone['peak_people']}</td></tr>"
        for zone in data["zones"]
    )
    return (
        "<h2>Статистика</h2>"
        + summary
        + '<table width="100%" cellspacing="0" cellpadding="6" border="1">'
        "<thead><tr><th>Зона</th><th>Посетители по ID</th>"
        "<th>Входы</th><th>Пик людей</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
