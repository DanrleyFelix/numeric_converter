from dataclasses import replace
from pathlib import Path

from src.core.binary_workbench.mips_r3000a import (
    PsxMipsR3000ACodec,
    editor_mips_instruction,
)
from src.core.binary_workbench.version_overlays import (
    without_blank_instruction_overlays,
)
from src.modules.dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchVersionDTO

ROW_BYTES = 4
NOP_BYTES = "00000000"


def compact_binary_context_overlays(
    context: BinaryWorkbenchTabContextDTO,
) -> BinaryWorkbenchTabContextDTO:
    byte_overlays, instruction_overlays = without_blank_instruction_overlays(
        dict(context.byte_overlays),
        dict(context.instruction_overlays),
    )
    source = Path(context.source_path) if context.source_path else None
    versions = [
        compact_binary_version_overlays(source, version)
        for version in context.versions
    ]
    if (
        context.kind == "binary"
        and source is not None
        and source.exists()
        and (byte_overlays or instruction_overlays)
    ):
        byte_overlays, instruction_overlays = _without_source_overlays(
            source,
            byte_overlays,
            instruction_overlays,
            context.active_version_name,
        )
    version_dirty = context.version_dirty and bool(
        context.active_version_name or byte_overlays or instruction_overlays
    )
    if (
        byte_overlays == context.byte_overlays
        and instruction_overlays == context.instruction_overlays
        and version_dirty == context.version_dirty
        and versions == context.versions
    ):
        return context
    return replace(
        context,
        byte_overlays=byte_overlays,
        instruction_overlays=instruction_overlays,
        version_dirty=version_dirty,
        versions=versions,
    )


def compact_binary_version_overlays(
    source: Path | None,
    version: BinaryWorkbenchVersionDTO,
) -> BinaryWorkbenchVersionDTO:
    if source is None or not source.exists() or not (version.rows or version.instruction_overlays):
        return version
    byte_overlays = {
        row.offsets.get("File", "0x00000000"): row.bytes_text
        for row in version.rows
    }
    byte_overlays, instruction_overlays = _without_source_overlays(
        source,
        byte_overlays,
        dict(version.instruction_overlays),
        version.name,
    )
    rows = [
        row
        for row in version.rows
        if row.offsets.get("File", "0x00000000") in byte_overlays
    ]
    if rows == version.rows and instruction_overlays == version.instruction_overlays:
        return version
    return replace(version, rows=rows, instruction_overlays=instruction_overlays)


def _without_source_overlays(
    path: Path,
    byte_overlays: dict[str, str],
    instruction_overlays: dict[str, str],
    active_version_name: str | None,
) -> tuple[dict[str, str], dict[str, str]]:
    codec = PsxMipsR3000ACodec()
    redundant_instructions: set[str] = set()
    with path.open("rb") as source:
        byte_overlays = {
            offset: value
            for offset, value in byte_overlays.items()
            if _source_bytes(source, offset, value) != _normalized_bytes(value)
        }
        for offset, instruction in instruction_overlays.items():
            source.seek(int(offset, 16))
            data = source.read(ROW_BYTES).ljust(ROW_BYTES, b"\x00")
            decoded = editor_mips_instruction(codec.disassemble(data, int(offset, 16)), int(offset, 16))
            if instruction.strip().casefold() == decoded.strip().casefold():
                redundant_instructions.add(offset)
    instruction_overlays = {
        offset: instruction
        for offset, instruction in instruction_overlays.items()
        if offset not in redundant_instructions
    }
    if redundant_instructions and active_version_name is None:
        return _without_legacy_nop_corruption(byte_overlays, instruction_overlays)
    return byte_overlays, instruction_overlays


def _source_bytes(source, offset: str, value: str) -> str:
    source.seek(int(offset, 16))
    return source.read(len(_normalized_bytes(value)) // 2).hex().upper()


def _normalized_bytes(value: str) -> str:
    return "".join(value.split()).upper()


def _without_legacy_nop_corruption(
    byte_overlays: dict[str, str],
    instruction_overlays: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    invalid = {
        offset
        for offset, instruction in instruction_overlays.items()
        if instruction.strip().casefold() == "nop"
        and _normalized_bytes(byte_overlays.get(offset, "")) == NOP_BYTES
    }
    return (
        {offset: value for offset, value in byte_overlays.items() if offset not in invalid},
        {offset: instruction for offset, instruction in instruction_overlays.items() if offset not in invalid},
    )
