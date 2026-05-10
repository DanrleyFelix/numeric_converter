from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT


def resolve_go_to_offsets(
    context: BinaryWorkbenchTabContextDTO,
    target: str,
    raw: str,
) -> list[int]:
    if not raw:
        return []
    try:
        if target == BINARY_WORKBENCH_TEXT.FILE_OFFSET_TARGET:
            return [int(raw, 0)]
        if target in context.reference_offset_bases:
            base = int(context.reference_offset_bases.get(target, "0x0"), 0)
            return [int(raw, 0) - base]
        sectors = lba_sectors()
        if target in sectors:
            return [int(raw, 0) * sectors[target]]
        if target == BINARY_WORKBENCH_TEXT.LABEL_TARGET:
            return offsets_from_strings([symbol_value(context.labels, raw)])
        if target == BINARY_WORKBENCH_TEXT.EQUATE_TARGET:
            return offsets_from_strings(symbol_offsets(context.symbol_offsets, raw))
        if target == BINARY_WORKBENCH_TEXT.VARIABLE_TARGET:
            return offsets_from_strings(symbol_offsets(context.symbol_offsets, raw))
        if target == BINARY_WORKBENCH_TEXT.INTERNAL_FILE_TARGET:
            return internal_file_offsets(context, raw)
        return []
    except ValueError:
        return []


def internal_file_offsets(context: BinaryWorkbenchTabContextDTO, raw: str) -> list[int]:
    target = next((item for item in context.internal_files if item.name.lower() == raw.lower()), None)
    if target is not None:
        return [target.start_lba * context.lba_sector_size]
    return [int(raw, 0) * context.lba_sector_size]


def symbol_value(values: dict[str, str], key: str) -> str:
    if key in values:
        return values[key]
    lowered = key.lower()
    return next((value for name, value in values.items() if name.lower() == lowered), "")


def symbol_offsets(values: dict[str, list[str]], key: str) -> list[str]:
    if key in values:
        return values[key]
    lowered = key.lower()
    return next((offsets for name, offsets in values.items() if name.lower() == lowered), [])


def lba_sectors() -> dict[str, int]:
    return {
        BINARY_WORKBENCH_TEXT.LBA_2048_TARGET: 2048,
        BINARY_WORKBENCH_TEXT.LBA_2334_TARGET: 2334,
        BINARY_WORKBENCH_TEXT.LBA_2352_TARGET: 2352,
    }


def offsets_from_strings(values: list[str]) -> list[int]:
    offsets: list[int] = []
    for value in values:
        try:
            offsets.append(int(value, 0))
        except ValueError:
            continue
    return offsets
