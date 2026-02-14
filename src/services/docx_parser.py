"""Парсер DOCX-файлов с описанием целей Directum Targets."""

import io
from typing import BinaryIO
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def parse_docx_bytes(content: bytes) -> str:
    """
    Извлекает текст из DOCX-файла, переданного в виде байтов.

    Args:
        content: Байтовое содержимое DOCX-файла.

    Returns:
        str: Текстовое содержимое документа (заголовки, абзацы, таблицы).

    Raises:
        ValueError: Если файл не является валидным DOCX-документом.
    """
    try:
        doc = Document(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Не удалось открыть DOCX-файл: {e}") from e

    return _extract_document_text(doc)


def parse_docx_file(file_path: str) -> str:
    """
    Извлекает текст из DOCX-файла по пути.

    Args:
        file_path: Путь к DOCX-файлу.

    Returns:
        str: Текстовое содержимое документа.

    Raises:
        FileNotFoundError: Если файл не найден.
        ValueError: Если файл не является валидным DOCX-документом.
    """
    import os
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    try:
        doc = Document(file_path)
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"Не удалось открыть DOCX-файл: {e}") from e

    return _extract_document_text(doc)


def _extract_document_text(doc: Document) -> str:
    """
    Извлекает структурированный текст из объекта Document.

    Обрабатывает заголовки, абзацы и таблицы.

    Args:
        doc: Объект python-docx Document.

    Returns:
        str: Текстовое содержимое документа.
    """
    parts = []

    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "p":
            paragraph = Paragraph(element, doc)
            text = paragraph.text.strip()
            if not text:
                continue

            # Определяем уровень заголовка
            style_name = paragraph.style.name if paragraph.style else ""
            if "Heading 1" in style_name or style_name == "1":
                parts.append(f"\n# {text}")
            elif "Heading 2" in style_name or style_name == "2":
                parts.append(f"\n## {text}")
            elif "Heading 3" in style_name or style_name == "3":
                parts.append(f"\n### {text}")
            else:
                parts.append(text)

        elif tag == "tbl":
            table = Table(element, doc)
            table_text = _extract_table_text(table)
            if table_text:
                parts.append(table_text)

    return "\n".join(parts)


def _extract_table_text(table: Table) -> str:
    """
    Извлекает текст из таблицы DOCX в виде строки.

    Args:
        table: Объект таблицы python-docx.

    Returns:
        str: Текстовое представление таблицы.
    """
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            cell_text = cell.text.strip().replace("\n", " ")
            cells.append(cell_text)
        if any(cells):
            rows.append(" | ".join(cells))

    if not rows:
        return ""

    result = "\n[ТАБЛИЦА]\n"
    result += "\n".join(rows)
    result += "\n[/ТАБЛИЦА]"
    return result
