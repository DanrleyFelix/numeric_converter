from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QPlainTextEdit

from src.modules.constants import HEX_DIGIT_PATTERN

IMMEDIATE_TOKEN = re.compile(rf"(?<![\w$])[-+]?(?:0x{HEX_DIGIT_PATTERN}+|\d+)(?![\w])")
MEMORY_OPERAND_TOKEN = re.compile(rf"(?<![\w$])[-+]?(?:0x{HEX_DIGIT_PATTERN}+|\d+)\(\$?[A-Za-z][A-Za-z0-9_]*\)")


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


def immediate_token_at_cursor(editor: QPlainTextEdit) -> ImmediateToken | None:
    return _token_at_cursor(editor, IMMEDIATE_TOKEN)


def variable_token_at_cursor(editor: QPlainTextEdit) -> ImmediateToken | None:
    return _token_at_cursor(editor, MEMORY_OPERAND_TOKEN) or immediate_token_at_cursor(editor)


def _token_at_position(editor: QPlainTextEdit, position: QPoint, pattern: re.Pattern[str]) -> ImmediateToken | None:
    cursor = editor.cursorForPosition(position)
    return _token_at_block_position(cursor.block(), cursor.positionInBlock(), pattern)


def _token_at_cursor(editor: QPlainTextEdit, pattern: re.Pattern[str]) -> ImmediateToken | None:
    cursor = editor.textCursor()
    return _token_at_block_position(cursor.block(), cursor.positionInBlock(), pattern)


def _token_at_block_position(block_ref, column: int, pattern: re.Pattern[str]) -> ImmediateToken | None:
    block = block_ref.text()
    for match in pattern.finditer(block):
        if match.start() <= column <= match.end():
            return ImmediateToken(
                match.group(),
                block_ref.position() + match.start(),
                block_ref.position() + match.end(),
            )
    return None
