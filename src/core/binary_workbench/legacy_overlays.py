from dataclasses import replace
from pathlib import Path

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_FILE_OFFSET as FIRST_OFFSET,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO

NOP_BYTES = "00000000"


def discard_legacy_nop_overlays(
    context: BinaryWorkbenchTabContextDTO,
) -> BinaryWorkbenchTabContextDTO:
    if context.kind != "binary" or context.active_version_name is None:
        return context
    protected = _active_version_offsets(context)
    invalid = {
        offset
        for offset, instruction in context.instruction_overlays.items()
        if offset == FIRST_OFFSET
        and offset not in protected
        and instruction.strip().casefold() == "nop"
        and _normalized_bytes(context.byte_overlays.get(offset, "")) == NOP_BYTES
        and _replaces_source_bytes(context, offset)
    }
    if not invalid:
        return context
    byte_overlays = {
        offset: value
        for offset, value in context.byte_overlays.items()
        if offset not in invalid
    }
    instruction_overlays = {
        offset: instruction
        for offset, instruction in context.instruction_overlays.items()
        if offset not in invalid
    }
    return replace(
        context,
        byte_overlays=byte_overlays,
        instruction_overlays=instruction_overlays,
        version_dirty=context.version_dirty and bool(byte_overlays or instruction_overlays),
    )


def _active_version_offsets(context: BinaryWorkbenchTabContextDTO) -> set[str]:
    version = next(
        (
            item
            for item in context.versions
            if item.name == context.active_version_name
        ),
        None,
    )
    if version is None:
        return set()
    return {
        *version.instruction_overlays.keys(),
        *(row.offsets.get("File", "0x00000000") for row in version.rows),
    }


def _normalized_bytes(value: str) -> str:
    return "".join(value.split()).upper()


def _replaces_source_bytes(context: BinaryWorkbenchTabContextDTO, offset: str) -> bool:
    source = Path(context.source_path) if context.source_path else None
    if source is None or not source.exists():
        return False
    with source.open("rb") as stream:
        stream.seek(int(offset, 16))
        return stream.read(ROW_BYTES).hex().upper() != NOP_BYTES
