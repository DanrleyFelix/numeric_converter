from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS
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
            return file_offset_matches(context, raw)
        if target in context.reference_offset_bases:
            return reference_offset_matches(context, target, raw)
        sectors = lba_sectors()
        if target in sectors:
            return [int(raw, 10) * sectors[target]]
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
    return []


def file_offset_matches(context: BinaryWorkbenchTabContextDTO, raw: str) -> list[int]:
    value = raw.strip()
    if not value:
        return []
    size = file_size(context)
    matches: list[int] = []
    while value:
        offset = int(value, 16)
        if size <= 0 or offset < size:
            matches.append(offset)
        else:
            break
        value = f"{value}0"
    return matches


def reference_offset_matches(context: BinaryWorkbenchTabContextDTO, target: str, raw: str) -> list[int]:
    for value in reference_offset_values(raw):
        if matched := file_offset_for_reference_row(context, target, value):
            return matched
        offset = value - int(context.reference_offset_bases.get(target, "0x0"), 0)
        if offset < 0:
            continue
        size = file_size(context)
        if size > 0 and offset >= size:
            break
        return [offset]
    return []


def reference_offset_values(raw: str) -> list[int]:
    value = raw.strip()
    values: list[int] = []
    while value and len(value) <= 16:
        values.append(int(value, 16))
        value = f"{value}0"
    return values


def file_offset_for_reference_row(
    context: BinaryWorkbenchTabContextDTO,
    target: str,
    value: int,
) -> list[int]:
    for row in context.rows:
        try:
            if int(row.offsets.get(target, "-"), 0) == value:
                return [int(row.offsets.get("File", "-"), 0)]
        except ValueError:
            continue
    return []


def file_size(context: BinaryWorkbenchTabContextDTO) -> int:
    if context.file_size > 0:
        return context.file_size
    offsets: list[int] = []
    for row in context.rows:
        value = row.offsets.get("File", "-")
        if value == "-":
            continue
        try:
            offsets.append(int(value, 0))
        except ValueError:
            continue
    return max(offsets, default=-1) + 1


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
    targets = (
        BINARY_WORKBENCH_TEXT.LBA_2048_TARGET,
        BINARY_WORKBENCH_TEXT.LBA_2334_TARGET,
        BINARY_WORKBENCH_TEXT.LBA_2352_TARGET,
    )
    return dict(zip(targets, BINARY_WORKBENCH_LBA_SECTOR_SIZE_OPTIONS, strict=True))


def offsets_from_strings(values: list[str]) -> list[int]:
    offsets: list[int] = []
    for value in values:
        try:
            offsets.append(int(value, 0))
        except ValueError:
            continue
    return offsets
