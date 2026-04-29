from __future__ import annotations

from numbers import Number

from src.core.command_window.tokenizer.errors import TokenizerError
from src.core.command_window.tokenizer.token import Token, TokenType
from src.core.constants import BASE_PREFIXES, BINARY_DIGITS, DECIMAL_DIGITS, HEX_DIGITS


class NumberTokenReader:
    def __init__(self, text: str, start: int):
        self._text = text
        self._start = start
        self._pos = start

    def read(self) -> tuple[Token | None, int]:
        result = self._read_number_raw()
        if result is None:
            return None, self._start
        raw, value = result
        return Token(TokenType.NUMBER, raw, value, self._start), self._pos

    def _read_number_raw(self) -> tuple[str, Number] | None:
        float_value = self._read_decimal_float()
        if float_value is not None:
            return float_value
        base_number = self._read_prefixed_number()
        if base_number is not None:
            return base_number
        if self._current() in DECIMAL_DIGITS:
            digits = self._consume_allowed(DECIMAL_DIGITS)
            return digits, int(digits)
        return None

    def _read_decimal_float(self) -> tuple[str, float] | None:
        integer = self._consume_allowed(DECIMAL_DIGITS)
        if not integer:
            return None
        if self._current() != ".":
            self._pos = self._start
            return None
        self._pos += 1
        fractional = self._consume_allowed(DECIMAL_DIGITS)
        if not fractional:
            raise TokenizerError(f"Invalid float at position {self._start}")
        raw = f"{integer}.{fractional}"
        return raw, float(raw)

    def _read_prefixed_number(self) -> tuple[str, int] | None:
        for prefix, base in sorted(BASE_PREFIXES.items(), key=lambda item: -len(item[0])):
            if not self._text.startswith(prefix, self._pos):
                continue
            self._pos += len(prefix)
            digits = self._read_digits_for_base(base)
            if not digits:
                raise TokenizerError(f"Invalid number for base {base} at position {self._start}")
            if self._has_invalid_trailing_identifier_char():
                raise TokenizerError(
                    f"Invalid digit '{self._current()}' for base {base} at position {self._pos}"
                )
            return prefix + digits, int(digits, base)
        return None

    def _read_digits_for_base(self, base: int) -> str:
        if base == 2:
            return self._consume_allowed(BINARY_DIGITS)
        if base == 16:
            return self._consume_allowed(HEX_DIGITS)
        raise ValueError(f"Unsupported base {base}")

    def _consume_allowed(self, allowed: str) -> str:
        start = self._pos
        while not self._eof() and self._current() in allowed:
            self._pos += 1
        return self._text[start:self._pos]

    def _has_invalid_trailing_identifier_char(self) -> bool:
        if self._eof():
            return False
        current = self._current()
        return current.isalnum() or current == "_"

    def _current(self) -> str:
        if self._eof():
            return "\0"
        return self._text[self._pos]

    def _eof(self) -> bool:
        return self._pos >= len(self._text)
