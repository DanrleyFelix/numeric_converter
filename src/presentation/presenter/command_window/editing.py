from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.core.command_window.validator.errors import UnknownVariableError
from src.core.constants import MULTI_CHAR_OPERATORS

T = TypeVar("T")


def _has_stable_rhs_after_last_operator(text: str) -> bool:
    last_operator_end = -1
    index = 0

    while index < len(text):
        for operator in MULTI_CHAR_OPERATORS:
            if text.startswith(operator, index):
                last_operator_end = index + len(operator)
                index = last_operator_end
                break
        else:
            index += 1

    if last_operator_end == -1:
        return False
    return len(text) - last_operator_end > 2


def trim_invalid_suffix(
    text: str,
    validate_change: Callable[[str], object],
) -> str:
    if _has_stable_rhs_after_last_operator(text):
        return text

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
