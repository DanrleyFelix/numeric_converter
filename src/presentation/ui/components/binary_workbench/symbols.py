from __future__ import annotations

import re

from src.core.binary_workbench.symbol_values import merged_symbol_values
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def symbol_offsets(
    rows: list[BinaryWorkbenchRowDTO],
    variables: dict[str, str],
    equates: dict[str, str],
    labels: dict[str, str],
) -> dict[str, list[str]]:
    symbols = merged_symbol_values(variables=variables, equates=equates)
    values = {name: [] for name in [*symbols, *labels]}
    tokens = {
        name: re.compile(
            rf"(?<![A-Za-z0-9_])[_@]{re.escape(name)}(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        for name in symbols
    }
    for row in rows:
        offset = row.offsets.get("File", "0x00000000")
        if offset == "-":
            continue
        for name, token in tokens.items():
            if token.search(row.instruction):
                values[name].append(offset)
    for name, offset in labels.items():
        values[name] = [offset]
    return values
