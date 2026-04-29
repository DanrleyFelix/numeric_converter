from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.core.command_window.validator.errors import UnknownVariableError

T = TypeVar("T")


def trim_invalid_suffix(
    text: str,
    validate_change: Callable[[str], object],
) -> str:
    candidate = text
    while candidate:
        candidate = candidate[:-1]
        try:
            validate_change(candidate)
            return candidate
        except UnknownVariableError:
            return candidate
        except Exception:
            continue
    return ""


def append_limited(target: list[T], value: T, max_size: int) -> None:
    target.append(value)
    if len(target) > max_size:
        target.pop(0)
