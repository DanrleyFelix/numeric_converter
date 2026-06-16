from __future__ import annotations

from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import ROW_BYTES

BYTES_PANEL = "binary-workbench-bytes-panel"
HEX_CHARACTERS = frozenset("0123456789abcdefABCDEF")
DISPLAY_SEPARATOR = " "
MAX_LINE_HEX_CHARACTERS = ROW_BYTES * 2


def is_bytes_editor(editor) -> bool:
    return editor.objectName() == BYTES_PANEL


def bytes_insert_allowed(text: str, document_text: str, ranges: list[tuple[int, int]]) -> bool:
    if not text or any(char not in HEX_CHARACTERS for char in text):
        return False
    return bytes_replacement_allowed(text, document_text, ranges)


def bytes_replacement_allowed(text: str, document_text: str, ranges: list[tuple[int, int]]) -> bool:
    if not text or any(char not in HEX_CHARACTERS and char != DISPLAY_SEPARATOR for char in text):
        return False
    for start, end in ranges:
        if not _range_accepts_text(document_text, start, end, text):
            return False
    return True


def bytes_paste_replacement(
    text: str,
    document_text: str,
    start: int,
    end: int,
    allow_line_shift: bool,
) -> str | None:
    if not text or any(not _allowed_paste_character(char) for char in text):
        return None
    selected_text = document_text[start:end]
    if not allow_line_shift and "\n" in selected_text:
        replacement = _target_lines_replacement(_hex_stream(text), selected_text)
    else:
        replacement = _shift_replacement(text) if allow_line_shift else _format_hex_line(_hex_stream(text))
    if replacement is None:
        return None
    updated = f"{document_text[:start]}{replacement}{document_text[end:]}"
    return replacement if _document_is_valid(updated) else None


def bytes_delete_allowed(editor, previous: bool, allow_line_shift: bool) -> bool:
    cursor = editor.textCursor()
    text = editor.toPlainText()
    start, end = _delete_range(editor, previous)
    if start == end:
        return False
    crosses_line = "\n" in text[start:end]
    if crosses_line and not allow_line_shift:
        return False
    return _document_is_valid(f"{text[:start]}{text[end:]}")


def _range_accepts_text(document_text: str, start: int, end: int, text: str) -> bool:
    line_start, line_end = _line_bounds(document_text, start)
    if end > line_end:
        return False
    relative_start = start - line_start
    relative_end = end - line_start
    line = document_text[line_start:line_end]
    updated = f"{line[:relative_start]}{text}{line[relative_end:]}"
    return (
        all(char in HEX_CHARACTERS or char == DISPLAY_SEPARATOR for char in updated)
        and _hex_count(updated) <= MAX_LINE_HEX_CHARACTERS
    )


def _line_bounds(text: str, position: int) -> tuple[int, int]:
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    return start, len(text) if end < 0 else end


def _hex_count(text: str) -> int:
    return sum(1 for char in text if char in HEX_CHARACTERS)


def _allowed_paste_character(char: str) -> bool:
    return char in HEX_CHARACTERS or char.isspace()


def _hex_stream(text: str) -> str:
    return "".join(char for char in text if char in HEX_CHARACTERS)


def _format_hex_line(hex_text: str) -> str:
    return DISPLAY_SEPARATOR.join(
        hex_text[index : index + 2]
        for index in range(0, len(hex_text), 2)
    )


def _shift_replacement(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stream = _hex_stream(raw_line)
        if not stream:
            lines.append("")
            continue
        for index in range(0, len(stream), MAX_LINE_HEX_CHARACTERS):
            lines.append(_format_hex_line(stream[index : index + MAX_LINE_HEX_CHARACTERS]))
    return "\n".join(lines)


def _target_lines_replacement(hex_text: str, selected_text: str) -> str | None:
    capacities = [_hex_count(line) for line in selected_text.split("\n")]
    if len(hex_text) != sum(capacities):
        return None
    cursor = 0
    lines: list[str] = []
    for capacity in capacities:
        lines.append(_format_hex_line(hex_text[cursor : cursor + capacity]))
        cursor += capacity
    return "\n".join(lines)


def _delete_range(editor, previous: bool) -> tuple[int, int]:
    cursor = editor.textCursor()
    if cursor.hasSelection():
        return cursor.selectionStart(), cursor.selectionEnd()
    position = cursor.position()
    if previous:
        return max(0, position - 1), position
    return position, min(len(editor.toPlainText()), position + 1)


def _document_is_valid(text: str) -> bool:
    return all(_line_is_valid(line) for line in text.split("\n"))


def _line_is_valid(line: str) -> bool:
    return (
        all(char in HEX_CHARACTERS or char == DISPLAY_SEPARATOR for char in line)
        and _hex_count(line) <= MAX_LINE_HEX_CHARACTERS
    )
