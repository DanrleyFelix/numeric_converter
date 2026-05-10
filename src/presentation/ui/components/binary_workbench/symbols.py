from __future__ import annotations

from src.modules.dtos import BinaryWorkbenchRowDTO


def symbol_offsets(
    rows: list[BinaryWorkbenchRowDTO],
    variables: dict[str, str],
    equates: dict[str, str],
    labels: dict[str, str],
) -> dict[str, list[str]]:
    values = {name: [] for name in [*variables.keys(), *equates.keys(), *labels.keys()]}
    for row in rows:
        offset = row.offsets.get("File", "0x00000000")
        instruction = row.instruction.upper()
        for name in variables:
            if f"_{name.lstrip('_')}".upper() in instruction:
                values[name].append(offset)
        for name in equates:
            if f"@{name.lstrip('@')}".upper() in instruction:
                values[name].append(offset)
    for name, offset in labels.items():
        values[name] = [offset]
    return values
