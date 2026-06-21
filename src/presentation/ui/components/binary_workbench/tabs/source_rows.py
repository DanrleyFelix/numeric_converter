from pathlib import Path

from src.core.binary_workbench.mips_r3000a import (
    build_rows_from_bytes,
    build_rows_from_instructions,
    extract_labels_from_instructions,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO

DEFAULT_REFS = ["File"]
DEFAULT_REF_BASES = {"File": "0x00000000"}
ASSEMBLY_SUFFIXES = {".asm", ".s"}


def is_assembly_path(path: Path) -> bool:
    return path.suffix.lower() in ASSEMBLY_SUFFIXES


def reload_source_rows(
    path: Path,
    read_mode: str,
    offsets: list[str],
    block_size: int,
    offset_bases: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    return rows_from_path(path, resolve_read_mode(path, read_mode), offsets, block_size, offset_bases)


def load_more_binary_rows(
    path: Path,
    offsets: list[str],
    start_offset: int,
    block_size: int,
    offset_bases: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    if not path.exists():
        return []
    with path.open("rb") as source:
        source.seek(start_offset)
        data = source.read(block_size)
    return build_rows_from_bytes(data, offsets, start_offset, offset_bases)


def rows_from_path(
    path: Path,
    read_mode: str,
    offsets: list[str],
    block_size: int,
    offset_bases: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    if resolve_read_mode(path, read_mode) == "assembly":
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
        return build_rows_from_instructions(lines, offsets, offset_bases)
    return load_more_binary_rows(path, offsets, 0, block_size, offset_bases)


def resolve_read_mode(path: Path, requested: str) -> str:
    if requested == "auto":
        return "assembly" if is_assembly_path(path) else "bytes"
    return requested


def labels_from_path(path: Path, read_mode: str) -> dict[str, str]:
    if resolve_read_mode(path, read_mode) != "assembly" or not path.exists():
        return {}
    return extract_labels_from_instructions(
        path.read_text(encoding="utf-8", errors="replace").splitlines()
    )
