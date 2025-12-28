from src.models.command_window.tokenizer.token import Token, TokenType
from src.models.constants import (
    MULTI_CHAR_OPERATORS,
    IDENTIFIER_RE,
    WHITESPACE_RE,
    DECIMAL_DIGITS,
    BINARY_DIGITS,
    HEX_DIGITS,
    BASE_PREFIXES,
    UNARY_OPERATORS
)


class TokenizerError(Exception):
    pass


class Tokenizer:

    def __init__(self, text: str):
        self.prev_token: Token | None = None
        self.text = text
        self.pos = 0
        self.length = len(text)

    def _is_unary_position(self) -> bool:
        if self.prev_token is None:
            return True

        if self.prev_token.type in {
            TokenType.OPERATOR,
            TokenType.LPAREN,
        }:
            return True

        return False

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []

        while self.pos < self.length:
            match = WHITESPACE_RE.match(self.text, self.pos)
            if match:
                self.pos = match.end()
                continue

            char = self.text[self.pos]

            if char == "(":
                token = Token(TokenType.LPAREN, "(", "(", self.pos)
                tokens.append(token)
                self.pos += 1
                self.prev_token = token
                continue

            if char == ")":
                token = Token(TokenType.RPAREN, ")", ")", self.pos)
                tokens.append(token)
                self.pos += 1
                self.prev_token = token
                continue

            matched = self._match_operator()
            if matched:
                raw, can_be_unary = matched
                token = Token(
                    type=TokenType.OPERATOR,
                    value=raw,
                    raw=raw,
                    position=self.pos,
                    can_be_unary=can_be_unary)
                tokens.append(token)
                self.pos += len(raw)
                self.prev_token = token
                continue

            number = self._match_number()
            if number:
                raw, start = number
                token = Token(TokenType.NUMBER, raw, raw, start)
                tokens.append(token)
                self.prev_token = token
                continue

            ident = self._match_identifier()
            if ident:
                tokens.append(ident)
                self.prev_token = ident
                continue

            raise TokenizerError(f"Unknown token '{char}' at position {self.pos}")

        tokens.append(Token(TokenType.EOF, None, "", self.pos))
        return tokens

    def _match_operator(self):
        for op in MULTI_CHAR_OPERATORS:
            if self.text.startswith(op, self.pos):
                can_be_unary = (op in UNARY_OPERATORS and self._is_unary_position())
                return op, can_be_unary
        return None

    def _match_number(self):
        start = self.pos

        for prefix, base in sorted(BASE_PREFIXES.items(), key=lambda x: -len(x[0])):
            if self.text.startswith(prefix, self.pos):
                self.pos += len(prefix)

                if base == 2:
                    digits = self._consume(BINARY_DIGITS)
                elif base == 16:
                    digits = self._consume(HEX_DIGITS)
                else:
                    return None

                if not digits:
                    raise TokenizerError(f"Invalid number for base {base} at position {start}")

                return prefix + digits, start

        if self.text[self.pos] in DECIMAL_DIGITS:
            digits = self._consume(DECIMAL_DIGITS)
            return digits, start

        return None

    def _match_identifier(self):
        match = IDENTIFIER_RE.match(self.text, self.pos)
        if not match:
            return None

        raw = match.group(0)
        start = self.pos
        self.pos += len(raw)
        return Token(TokenType.IDENTIFIER, raw, raw, start)

    def _consume(self, allowed: str) -> str:
        start = self.pos
        while self.pos < self.length and self.text[self.pos] in allowed:
            self.pos += 1
        return self.text[start:self.pos]


__all__ = ["Tokenizer", "TokenizerError"]
