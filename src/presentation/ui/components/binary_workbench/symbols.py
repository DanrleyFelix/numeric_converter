from __future__ import annotations

from src.core.binary_workbench.symbol_values import merged_symbol_values
from src.core.binary_workbench.symbols.occurrences import SYMBOL_TOKEN
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def symbol_offsets(
    rows: list[BinaryWorkbenchRowDTO],
    variables: dict[str, str],
    equates: dict[str, str],
    labels: dict[str, str],
) -> dict[str, list[str]]:
    symbols = merged_symbol_values(variables=variables, equates=equates)
    values = {name: [] for name in [*symbols, *labels]}
    names_by_key = {name.casefold(): name for name in symbols}
    for row in rows:
        offset = row.offsets.get("File", "0x00000000")
        if offset == "-":
            continue
        found: set[str] = set()
        for token in SYMBOL_TOKEN.finditer(row.instruction):
            name = names_by_key.get(token.group(2).casefold())
            if name is not None and name not in found:
                values[name].append(offset)
                found.add(name)
    for name, offset in labels.items():
        values[name] = [offset]
    return values
