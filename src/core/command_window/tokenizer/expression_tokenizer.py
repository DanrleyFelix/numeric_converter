from __future__ import annotations

from typing import Optional

from src.core.command_window.tokenizer.errors import TokenizerError
from src.core.command_window.tokenizer.number_token_reader import NumberTokenReader
from src.core.command_window.tokenizer.textual_operator_normalizer import TextualOperatorNormalizer
from src.core.command_window.tokenizer.token import Token, TokenType
from src.core.constants import IDENTIFIER_RE, MULTI_CHAR_OPERATORS, WHITESPACE_RE


class Tokenizer:
    def __init__(self, text: str):
        self.text = text
        self.length = len(text)
        self.pos = 0

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while not self._eof():
            if self._skip_whitespace():
                continue
            token = (
                self._consume_number()
                or self._consume_identifier()
                or self._consume_parenthesis()
                or self._consume_operator()
            )
            if token is None:
                raise TokenizerError(f"Unknown token '{self._current()}' at position {self.pos}")
            tokens.append(token)
        tokens = TextualOperatorNormalizer(self.text, tokens).normalize()
        tokens.append(Token(TokenType.EOF, "", position=self.pos))
        return tokens

    def _consume_number(self) -> Optional[Token]:
        token, new_position = NumberTokenReader(self.text, self.pos).read()
        if token is not None:
            self.pos = new_position
        return token

    def _consume_identifier(self) -> Optional[Token]:
        match = IDENTIFIER_RE.match(self.text, self.pos)
        if not match:
            return None
        raw = match.group(0)
        start = self.pos
        self.pos += len(raw)
        return Token(TokenType.IDENTIFIER, raw, raw, start)

    def _consume_parenthesis(self) -> Optional[Token]:
        current = self._current()
        if current == "(":
            self.pos += 1
            return Token(TokenType.LPAREN, "(", "(", self.pos - 1)
        if current == ")":
            self.pos += 1
            return Token(TokenType.RPAREN, ")", ")", self.pos - 1)
        return None

    def _consume_operator(self) -> Optional[Token]:
        for operator in MULTI_CHAR_OPERATORS:
            if self.text.startswith(operator, self.pos):
                start = self.pos
                self.pos += len(operator)
                return Token(TokenType.OPERATOR, operator, operator, start)
        return None

    def _skip_whitespace(self) -> bool:
        match = WHITESPACE_RE.match(self.text, self.pos)
        if not match:
            return False
        self.pos = match.end()
        return True

    def _current(self) -> str:
        return "\0" if self._eof() else self.text[self.pos]

    def _eof(self) -> bool:
        return self.pos >= self.length
