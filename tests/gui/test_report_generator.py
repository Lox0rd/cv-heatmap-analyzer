from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QImage, QTextDocument

from src.export.report_generator import _build_document


def test_report_renders_markdown_with_qt_styles(qtbot, tmp_path):
    overlay = tmp_path / "heatmap_overlay.jpg"
    image = QImage(80, 60, QImage.Format.Format_RGB32)
    image.fill(0xff112233)
    local_image = tmp_path / "local.png"
    assert image.save(str(local_image))
    local_url = QUrl.fromLocalFile(str(local_image))
    markdown = f"""### Активность в зонах

- **Правый проход**: *заметное движение*
- Касса: `2` входа

| Зона | Входы |
| --- | --- |
| Касса | 2 |

![Локальное изображение]({local_url.toString()})

<b>Обычный текст</b>
"""
    report = _build_document(overlay, None, (markdown, image))
    heading = report.find("Активность в зонах").block()
    assert heading.blockFormat().headingLevel() > 0
    assert report.find("Правый проход").block().textList() is not None
    assert report.find("Правый проход").charFormat().fontWeight() == 700
    assert report.find("заметное движение").charFormat().fontItalic()
    assert report.find("Входы").currentTable().columns() == 2
    assert "###" not in report.toPlainText()
    assert "<b>Обычный текст</b>" in report.toPlainText()

    image_type = QTextDocument.ResourceType.ImageResource
    assert report.resource(image_type, local_url) is None
    assert not report.resource(image_type, QUrl("report:heatmap")).isNull()
