from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QPlainTextEdit

IMMEDIATE_TOKEN = re.compile(r"(?<![\w$])[-+]?(?:0x[0-9A-Fa-f]+|\d+)(?![\w])")
MEMORY_OPERAND_TOKEN = re.compile(r"(?<![\w$])[-+]?(?:0x[0-9A-Fa-f]+|\d+)\(\$?[A-Za-z][A-Za-z0-9_]*\)")


@dataclass(frozen=True)
class ImmediateToken:
    value: str
    start: int
    end: int


def immediate_at_position(editor: QPlainTextEdit, position: QPoint) -> str:
    token = immediate_token_at_position(editor, position)
    return token.value if token is not None else ""


def variable_value_at_position(editor: QPlainTextEdit, position: QPoint) -> str:
    token = variable_token_at_position(editor, position)
    return token.value if token is not None else ""


def immediate_token_at_position(editor: QPlainTextEdit, position: QPoint) -> ImmediateToken | None:
    return _token_at_position(editor, position, IMMEDIATE_TOKEN)


def variable_token_at_position(editor: QPlainTextEdit, position: QPoint) -> ImmediateToken | None:
    return _token_at_position(editor, position, MEMORY_OPERAND_TOKEN) or immediate_token_at_position(editor, position)


def _token_at_position(editor: QPlainTextEdit, position: QPoint, pattern: re.Pattern[str]) -> ImmediateToken | None:
    cursor = editor.cursorForPosition(position)
    block_ref = cursor.block()
    block = block_ref.text()
    column = cursor.positionInBlock()
    for match in pattern.finditer(block):
        if match.start() <= column <= match.end():
            return ImmediateToken(
                match.group(),
                block_ref.position() + match.start(),
                block_ref.position() + match.end(),
            )
    return None
