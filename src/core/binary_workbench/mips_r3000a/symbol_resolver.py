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
        *,
        jump_file_offset_base: int = JUMP_FILE_OFFSET_BASE,
    ) -> None:
        self._labels = _normalized(labels)
        self._variables = _normalized(variables, "_")
        self._equates = _normalized(equates, "@")
        self._jump_file_offset_base = jump_file_offset_base

    @classmethod
    def from_symbol_maps(
        cls,
        maps: tuple[dict[str, str], dict[str, str], dict[str, str]],
    ) -> "MipsSymbolResolver":
        """Reuse highlighter lookup maps without copying a large catalog."""

        resolver = cls()
        resolver._labels, resolver._variables, resolver._equates = maps
        return resolver

    def replace(self, text: str, address: int, mnemonic: str) -> str:
        """Replace known symbols in one instruction without scanning every symbol."""

        def replacement(match: re.Match[str]) -> str:
            token = match.group("token")
            normalized = token.casefold()
            if token.startswith("_"):
                return self._variables.get(normalized, token)
            if token.startswith("@"):
                return self._equates.get(normalized, token)
            value = self._labels.get(normalized)
            if value is None:
                return token
            label_offset = _safe_int(value, address)
            target = (
                label_offset + self._jump_file_offset_base
                if mnemonic in J_OPCODES
                else _label_target(label_offset, address)
            )
            return f"0x{target:x}"

        return SYMBOL_TOKEN.sub(replacement, text)

    def with_labels(self, labels: Mapping[str, str]) -> "MipsSymbolResolver":
        """Replace the small label map while sharing large Symbol lookup maps."""

        resolver = type(self)()
        resolver._labels = _normalized(labels)
        resolver._variables = self._variables
        resolver._equates = self._equates
        resolver._jump_file_offset_base = self._jump_file_offset_base
        return resolver


def _normalized(
    values: Mapping[str, str] | None,
    prefix: str = "",
) -> dict[str, str]:
    """Normalize one symbol mapping for resolver reuse across source lines."""

    return {
        f"{prefix}{str(name).lstrip('_@')}".casefold(): str(value)
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
