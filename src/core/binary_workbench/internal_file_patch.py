from __future__ import annotations

from dataclasses import dataclass

from src.core.binary_workbench.internal_file_reader import InternalFileView
from src.core.binary_workbench.internal_offset_mapper import InternalOffsetMapper
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


def binary_overlays_from_internal_overlays(
    mapper: InternalOffsetMapper,
    overlays: dict[str, str],
) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for offset_text, bytes_text in sorted(overlays.items()):
        internal_offset = int(offset_text, 16)
        data = bytes.fromhex(bytes_text.replace(" ", ""))
        for chunk in mapper.chunks_for_internal_range(internal_offset, len(data)):
            source_start = chunk.internal_offset - internal_offset
            piece = data[source_start : source_start + chunk.size]
            mapped[f"0x{chunk.binary_offset:08X}"] = _bytes_text(piece)
    return mapped


def internal_overlays_from_binary_overlays(
    mapper: InternalOffsetMapper,
    overlays: dict[str, str],
) -> dict[str, str]:
    segments: list[tuple[int, bytes]] = []
    for offset_text, bytes_text in sorted(overlays.items()):
        binary_offset = int(offset_text, 16)
        data = bytes.fromhex(bytes_text.replace(" ", ""))
        for chunk in mapper.chunks_for_binary_range(binary_offset, len(data)):
            source_start = chunk.binary_offset - binary_offset
            piece = data[source_start : source_start + chunk.size]
            segments.append((chunk.internal_offset, piece))
    merged: list[tuple[int, bytes]] = []
    for internal_offset, data in sorted(segments):
        if merged and merged[-1][0] + len(merged[-1][1]) == internal_offset:
            previous_offset, previous_data = merged[-1]
            merged[-1] = (previous_offset, previous_data + data)
            continue
        merged.append((internal_offset, data))
    return {
        f"0x{internal_offset:08X}": _bytes_text(data)
        for internal_offset, data in merged
    }


def _bytes_text(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)
