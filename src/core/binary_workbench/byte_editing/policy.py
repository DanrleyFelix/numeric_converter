from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from src.core.binary_workbench.mips_r3000a.comments import split_comment
from src.core.binary_workbench.mips_r3000a.source_line_rows import split_label


class ByteRowAccess(Enum):
    """Describe which direct Bytes operations preserve one Assembly row."""

    EDITABLE = auto()
    ASSEMBLY_ONLY = auto()


class ByteEditViolation(Enum):
    """Explain why a direct Bytes operation must be rejected."""

    NONE = auto()
    ASSEMBLY_ONLY = auto()
    ROW_REMOVAL = auto()


@dataclass(frozen=True)
class ByteRowPolicy:
    """Stable edit and projection policy derived from one Assembly source row."""

    access: ByteRowAccess
    show_placeholder: bool = False
    removable_from_bytes: bool = False


def byte_row_policy(source: str, emits_bytes: bool) -> ByteRowPolicy:
    """Classify direct Bytes access without assembling or mutating the source."""

    code, marker, _ = split_comment(source)
    stripped = code.strip()
    if _is_directive(stripped):
        return ByteRowPolicy(ByteRowAccess.ASSEMBLY_ONLY, True)
    label, instruction = split_label(stripped)
    if label:
        return ByteRowPolicy(
            ByteRowAccess.EDITABLE,
            show_placeholder=not instruction,
        )
    if not stripped and marker:
        return ByteRowPolicy(ByteRowAccess.EDITABLE, True)
    if marker and emits_bytes:
        return ByteRowPolicy(ByteRowAccess.EDITABLE)
    return ByteRowPolicy(
        ByteRowAccess.EDITABLE,
        removable_from_bytes=not marker and not label,
    )


def _is_directive(code: str) -> bool:
    # Invalid or partially typed directives are source constructs too.  They
    # must be repaired in Assembly instead of becoming editable byte rows.
    return code.startswith("*")
