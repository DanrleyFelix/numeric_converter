from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    NUMBER = auto()
    IDENTIFIER = auto()
    OPERATOR = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: any
    raw: str
    position: int
    can_be_unary: bool = False


__all__ = ["Token", "TokenType"]

