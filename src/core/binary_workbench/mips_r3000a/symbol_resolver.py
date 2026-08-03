from __future__ import annotations

import re
from collections.abc import Mapping

from src.core.binary_workbench.mips_r3000a.constants import (
    JUMP_FILE_OFFSET_BASE,
    J_OPCODES,
)

SYMBOL_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(?P<token>[@_]?[A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])"
)


class MipsSymbolResolver:
    """Resolve instruction symbols through constant-time case-insensitive lookups."""

    def __init__(
        self,
        labels: Mapping[str, str] | None = None,
        variables: Mapping[str, str] | None = None,
        equates: Mapping[str, str] | None = None,
    ) -> None:
        self._labels = _normalized(labels)
        self._variables = _normalized(variables)
        self._equates = _normalized(equates)

    def replace(self, text: str, address: int, mnemonic: str) -> str:
        """Replace known symbols in one instruction without scanning every symbol."""

        def replacement(match: re.Match[str]) -> str:
            token = match.group("token")
            normalized = token.casefold()
            if token.startswith("_"):
                return self._variables.get(normalized.lstrip("_"), token)
            if token.startswith("@"):
                return self._equates.get(normalized.lstrip("@"), token)
            value = self._labels.get(normalized)
            if value is None:
                return token
            label_offset = _safe_int(value, address)
            target = (
                label_offset + JUMP_FILE_OFFSET_BASE
                if mnemonic in J_OPCODES
                else _label_target(label_offset, address)
            )
            return f"0x{target:x}"

        return SYMBOL_TOKEN.sub(replacement, text)


def _normalized(values: Mapping[str, str] | None) -> dict[str, str]:
    """Normalize one symbol mapping for resolver reuse across source lines."""

    return {
        str(name).lstrip("_@").casefold(): str(value)
        for name, value in (values or {}).items()
    }


def _label_target(value: int, address: int) -> int:
    """Project a file label into the active high-address instruction region."""

    return (address & ~0xFFFF) + value if value < 0x10000 <= address else value


def _safe_int(value: str, fallback: int) -> int:
    """Parse one configured symbol value or retain its instruction address."""

    try:
        return int(value, 0)
    except ValueError:
        return fallback
