from enum import Enum, auto


class TokenType(Enum):
    NUMBER = auto()
    IDENTIFIER = auto()
    OPERATOR = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


class Token:
    def __init__(self, type, raw: str, value: float | int | None = None, position=None):
        self.type = type
        self.raw = raw
        self.value = value
        self.position = position


__all__ = ["Token", "TokenType"]

