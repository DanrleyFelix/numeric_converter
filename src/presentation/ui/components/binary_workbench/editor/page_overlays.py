from __future__ import annotations

from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    file_offset,
)


def overlay_bytes(values: dict[str, str]) -> dict[int, bytes]:
    return {
        int(offset, 16): bytes.fromhex(bytes_text.replace(" ", ""))
        for offset, bytes_text in values.items()
    }


def apply_overlay_bytes(start: int, data: bytes, overlays: dict[int, bytes]) -> bytes:
    if not overlays:
        return data
    patched = bytearray(data)
    end = start + len(data)
    for patch_offset, patch_data in overlays.items():
        patch_end = patch_offset + len(patch_data)
        if patch_end <= start or patch_offset >= end:
            continue
        left = max(start, patch_offset)
        right = min(end, patch_end)
        source_left = left - patch_offset
        patched[left - start : right - start] = patch_data[source_left : source_left + (right - left)]
    return bytes(patched)


def instruction_overlays_with_changed_rows(
    overlays: dict[str, str],
    rows: list,
    previous_rows: list,
) -> dict[str, str]:
    updated = dict(overlays)
    previous_bytes = {file_offset(row): row.bytes_text for row in previous_rows}
    for row in rows:
        offset = file_offset(row)
        if offset != "-" and previous_bytes.get(offset) != row.bytes_text:
            updated[offset] = row.instruction
    return updated
