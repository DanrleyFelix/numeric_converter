from __future__ import annotations

import re

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QPlainTextEdit

IMMEDIATE_TOKEN = re.compile(r"(?<![\w$])[-+]?(?:0x[0-9A-Fa-f]+|\d+)(?![\w])")
MEMORY_OPERAND_TOKEN = re.compile(r"(?<![\w$])[-+]?(?:0x[0-9A-Fa-f]+|\d+)\(\$?[A-Za-z][A-Za-z0-9_]*\)")


def immediate_at_position(editor: QPlainTextEdit, position: QPoint) -> str:
    return _token_at_position(editor, position, IMMEDIATE_TOKEN)


def variable_value_at_position(editor: QPlainTextEdit, position: QPoint) -> str:
    return _token_at_position(editor, position, MEMORY_OPERAND_TOKEN) or immediate_at_position(editor, position)


def _token_at_position(editor: QPlainTextEdit, position: QPoint, pattern: re.Pattern[str]) -> str:
    cursor = editor.cursorForPosition(position)
    block = cursor.block().text()
    column = cursor.positionInBlock()
    for match in pattern.finditer(block):
        if match.start() <= column <= match.end():
            return match.group()
    return ""
