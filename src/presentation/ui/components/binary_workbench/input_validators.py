import keyword

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator, QValidator
from PySide6.QtWidgets import QLineEdit

from src.modules.constants import (
    DECIMAL_DIGITS,
    DECIMAL_INPUT_PATTERN as DECIMAL_INTEGER_PATTERN,
    HEX_INPUT_PATTERN as HEX_VALUE_PATTERN,
    HEX_LOWER_INPUT_PATTERN as HEX_BYTES_PATTERN,
)

PYTHON_IDENTIFIER_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"
PYTHON_IDENTIFIER_EXPRESSION = QRegularExpression(f"^{PYTHON_IDENTIFIER_PATTERN}$")


class PythonIdentifierValidator(QValidator):
    def validate(self, value: str, position: int) -> tuple[QValidator.State, str, int]:
        if not value:
            return QValidator.State.Intermediate, value, position
        allowed = all(character == "_" or character.isascii() and character.isalnum() for character in value)
        if not allowed or value[0] in DECIMAL_DIGITS:
            return QValidator.State.Invalid, value, position
        if PYTHON_IDENTIFIER_EXPRESSION.match(value).hasMatch() and not keyword.iskeyword(value):
            return QValidator.State.Acceptable, value, position
        return QValidator.State.Intermediate, value, position


def set_python_identifier_validator(editor: QLineEdit) -> None:
    editor.setValidator(PythonIdentifierValidator(editor))


def set_decimal_integer_validator(editor: QLineEdit) -> None:
    editor.setValidator(QRegularExpressionValidator(QRegularExpression(DECIMAL_INTEGER_PATTERN), editor))


def set_hex_value_validator(editor: QLineEdit) -> None:
    editor.setValidator(QRegularExpressionValidator(QRegularExpression(HEX_VALUE_PATTERN), editor))


def set_hex_bytes_validator(editor: QLineEdit) -> None:
    editor.setValidator(QRegularExpressionValidator(QRegularExpression(HEX_BYTES_PATTERN), editor))
