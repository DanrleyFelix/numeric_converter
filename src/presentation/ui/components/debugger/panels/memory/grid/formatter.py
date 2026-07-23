from __future__ import annotations

from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    normalize_bytes_text,
)


def memory_bytes_text(raw: str) -> str:
    """Format sixteen bytes as four explicit groups of four bytes."""

    tokens = normalize_bytes_text(raw, 1, True).split()
    return "  ".join(
        " ".join(tokens[index : index + 4])
        for index in range(0, len(tokens), 4)
    )


def memory_cell_text(data: bytes) -> str:
    """Format one fixed four-byte memory cell."""

    return " ".join(f"{value:02X}" for value in data)


def memory_cell_data(text: str) -> bytes | None:
    """Normalize at most four hexadecimal bytes and right-pad with zeroes."""

    if any(character not in "0123456789abcdefABCDEF \t\r\n" for character in text):
        return None
    compact = "".join(text.split())
    if len(compact) > 8:
        return None
    compact = compact.ljust(8, "0")
    try:
        return bytes.fromhex(compact)
    except ValueError:
        return None


def memory_paste_cells(text: str, capacity: int) -> tuple[bytes, ...] | None:
    """Split clipboard hexadecimal data without exceeding selected cells."""

    if capacity <= 0:
        return None
    if any(character not in "0123456789abcdefABCDEF \t\r\n" for character in text):
        return None
    compact = "".join(text.split())
    if len(compact) > capacity * 8:
        return None
    compact = compact + ("0" if len(compact) % 2 else "")
    return tuple(
        bytes.fromhex(compact[index : index + 8].ljust(8, "0"))
        for index in range(0, len(compact), 8)
    )
