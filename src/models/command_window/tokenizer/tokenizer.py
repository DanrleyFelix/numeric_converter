from __future__ import annotations

from typing import Optional, Tuple, Union, List

from src.models.command_window.tokenizer.token import Token, TokenType
from src.models.constants import (
    WHITESPACE_RE,
    IDENTIFIER_RE,
    MULTI_CHAR_OPERATORS,
    BASE_PREFIXES,
    DECIMAL_DIGITS,
    BINARY_DIGITS,
    HEX_DIGITS)

Number = Union[int, float]


class TokenizerError(Exception):
    pass


class Tokenizer:
    def __init__(self, text: str):
        self.text: str = text
        self.length: int = len(text)
        self.pos: int = 0
        self.prev_token: Optional[Token] = None

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while not self._eof():
            if self._skip_whitespace():
                continue

            token = (
                self._consume_signed_number()
                or self._consume_number()
                or self._consume_identifier()
                or self._consume_parenthesis()
                or self._consume_operator())

            if token is None:
                raise TokenizerError(
                    f"Unknown token '{self._current()}' at position {self.pos}")

            tokens.append(token)
            self.prev_token = token

        tokens.append(Token(TokenType.EOF, "", position=self.pos))
        return tokens

    def _can_start_signed_number(self) -> bool:
        if self.prev_token is None:
            return True

        return self.prev_token.type in {
            TokenType.OPERATOR,
            TokenType.LPAREN}

    def _consume_signed_number(self) -> Optional[Token]:
        if self._current() not in "+-":
            return None

        if not self._can_start_signed_number():
            return None

        start = self.pos
        sign = self._current()
        self.pos += 1

        number = self._consume_number()
        if number is None:
            self.pos = start
            return None

        value = -number.value if sign == "-" else number.value

        return Token(
            TokenType.NUMBER,
            raw=sign + number.raw,
            value=value,
            position=start)

    def _consume_number(self) -> Optional[Token]:
        start = self.pos
        result = self._consume_number_raw()

        if result is None:
            return None

        raw, value = result
        return Token(TokenType.NUMBER, raw, value, start)

    def _consume_identifier(self) -> Optional[Token]:
        match = IDENTIFIER_RE.match(self.text, self.pos)
        if not match:
            return None

        raw = match.group(0)
        start = self.pos
        self.pos += len(raw)

        return Token(TokenType.IDENTIFIER, raw, raw, start)

    def _consume_operator(self) -> Optional[Token]:
        for op in MULTI_CHAR_OPERATORS:
            if self.text.startswith(op, self.pos):
                start = self.pos
                self.pos += len(op)

                return Token(
                    TokenType.OPERATOR,
                    raw=op,
                    value=op,
                    position=start)
        return None

    def _consume_parenthesis(self) -> Optional[Token]:
        ch = self._current()

        if ch == "(":
            self.pos += 1
            return Token(TokenType.LPAREN, "(", "(", self.pos - 1)

        if ch == ")":
            self.pos += 1
            return Token(TokenType.RPAREN, ")", ")", self.pos - 1)

        return None

    def _consume_number_raw(self) -> Optional[Tuple[str, Number]]:
        start = self.pos

        float_value = self._consume_decimal_float()
        if float_value:
            return float_value

        for prefix, base in sorted(BASE_PREFIXES.items(), key=lambda x: -len(x[0])):
            if self.text.startswith(prefix, self.pos):
                self.pos += len(prefix)
                digits = self._consume_digits(base)

                if not digits:
                    raise TokenizerError(f"Invalid number for base {base} at position {start}")

                if not self._eof():
                    next_char = self._current()
                    if next_char.isalnum() or next_char == "_":
                        raise TokenizerError(f"Invalid digit '{next_char}' for base {base} at position {self.pos}")

                return prefix + digits, int(digits, base)

        if self._current() in DECIMAL_DIGITS:
            digits = self._consume(DECIMAL_DIGITS)
            return digits, int(digits)

        return None

    def _consume_decimal_float(self) -> Optional[Tuple[str, float]]:
        start = self.pos

        integer = self._consume(DECIMAL_DIGITS)
        if not integer:
            return None

        if self._current() != ".":
            self.pos = start
            return None

        self.pos += 1
        fractional = self._consume(DECIMAL_DIGITS)

        if not fractional:
            raise TokenizerError(f"Invalid float at position {start}")

        raw = f"{integer}.{fractional}"
        return raw, float(raw)

    def _consume_digits(self, base: int) -> str:
        if base == 2:
            return self._consume(BINARY_DIGITS)
        if base == 16:
            return self._consume(HEX_DIGITS)
        raise ValueError(f"Unsupported base {base}")

    def _consume(self, allowed: str) -> str:
        start = self.pos
        while not self._eof() and self._current() in allowed:
            self.pos += 1
        return self.text[start:self.pos]

    def _skip_whitespace(self) -> bool:
        match = WHITESPACE_RE.match(self.text, self.pos)
        if not match:
            return False

        self.pos = match.end()
        return True

    def _current(self) -> str:
        if self._eof():
            return "\0"
        return self.text[self.pos]

    def _eof(self) -> bool:
        return self.pos >= self.length
