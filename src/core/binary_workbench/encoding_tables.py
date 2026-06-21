from __future__ import annotations

from src.modules.binary_workbench_constants import ANSI_WINDOWS_ENCODING, BINARY_WORKBENCH_ANSI_TABLE_NAME
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEncodingTableDTO,
)

UNMAPPED_BYTE = "."


def ansi_windows_values() -> dict[int, str]:
    values: dict[int, str] = {}
    for byte in range(256):
        try:
            character = bytes((byte,)).decode(ANSI_WINDOWS_ENCODING)
        except UnicodeDecodeError:
            continue
        if character.isprintable():
            values[byte] = character
    return values


def encoding_table_from_payload(
    raw: object,
    name: str,
) -> BinaryWorkbenchEncodingTableDTO | None:
    if not isinstance(raw, dict) or not name.strip():
        return None
    values: dict[int, str] = {}
    for raw_key, raw_value in raw.items():
        byte = _byte_key(raw_key)
        if byte is None or not _valid_text(raw_value):
            return None
        values[byte] = raw_value
    if not values:
        return None
    return BinaryWorkbenchEncodingTableDTO(name=name.strip(), values=values)


def enabled_encoding_values(
    tables: list[BinaryWorkbenchEncodingTableDTO],
    enabled_names: list[str],
) -> dict[int, str]:
    custom = {table.name: table.values for table in tables}
    merged: dict[int, str] = {}
    for name in enabled_names:
        values = ansi_windows_values() if name == BINARY_WORKBENCH_ANSI_TABLE_NAME else custom.get(name, {})
        for byte, text in values.items():
            merged.setdefault(byte, text)
    return merged


def encoding_table_conflicts(
    name: str,
    enabled_names: list[str],
    tables: list[BinaryWorkbenchEncodingTableDTO],
) -> bool:
    candidate = enabled_encoding_values(tables, [name])
    active = enabled_encoding_values(tables, enabled_names)
    return bool(candidate.keys() & active.keys())


def decode_bytes(data: bytes, values: dict[int, str]) -> str:
    return "".join(values.get(byte, UNMAPPED_BYTE) for byte in data)


def decode_hex_bytes(text: str, values: dict[int, str]) -> str:
    try:
        return decode_bytes(bytes.fromhex(text.replace(" ", "")), values)
    except ValueError:
        return ""


def _byte_key(raw: object) -> int | None:
    try:
        value = raw if isinstance(raw, int) else int(str(raw), 0)
    except (TypeError, ValueError):
        return None
    return value if 0 <= value <= 0xFF else None


def _valid_text(raw: object) -> bool:
    return isinstance(raw, str) and bool(raw) and "\n" not in raw and "\r" not in raw
