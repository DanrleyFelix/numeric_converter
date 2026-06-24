from __future__ import annotations

from dataclasses import dataclass

from src.core.binary_workbench.internal_file_reader import InternalFileView
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


@dataclass(frozen=True)
class InternalFilePatch:
    internal_offset: int
    original_bytes: bytes
    modified_bytes: bytes


def patches_from_overlays(
    view: InternalFileView,
    overlays: dict[str, str],
) -> list[InternalFilePatch]:
    patches: list[InternalFilePatch] = []
    for offset_text, bytes_text in sorted(overlays.items()):
        internal_offset = int(offset_text, 16)
        modified = bytes.fromhex(bytes_text.replace(" ", ""))
        original = view.read_uncached(internal_offset, len(modified), {})
        if original and modified[: len(original)] != original:
            patches.append(InternalFilePatch(internal_offset, original, modified[: len(original)]))
    return patches


def patches_from_version_rows(rows: list[BinaryWorkbenchRowDTO]) -> list[InternalFilePatch]:
    patches: list[InternalFilePatch] = []
    for row in rows:
        internal_offset = int(row.offsets.get("File", "0x0"), 16)
        original = bytes.fromhex(row.original_bytes_text.replace(" ", ""))
        modified = bytes.fromhex(row.bytes_text.replace(" ", ""))
        if modified != original:
            patches.append(InternalFilePatch(internal_offset, original, modified))
    return patches
