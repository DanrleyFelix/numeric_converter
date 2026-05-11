from __future__ import annotations

import re

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QPlainTextEdit

IMMEDIATE_TOKEN = re.compile(r"(?<![\w$])[-+]?(?:0x[0-9A-Fa-f]+|\d+)(?![\w])")


def immediate_at_position(editor: QPlainTextEdit, position: QPoint) -> str:
    cursor = editor.cursorForPosition(position)
    block = cursor.block().text()
    column = cursor.positionInBlock()
    for match in IMMEDIATE_TOKEN.finditer(block):
        if match.start() <= column <= match.end():
            return match.group()
    return ""
