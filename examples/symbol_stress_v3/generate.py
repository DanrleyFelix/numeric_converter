from __future__ import annotations

import json
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.binary_workbench.symbols.compatibility import (
    LegacySymbolsPayloadAdapter,
    SYMBOL_SCHEMA_VERSION,
    definitions_payload,
)
from src.core.binary_workbench.symbols.definitions import SymbolScope

LOCAL_COUNT = 1_500
GLOBAL_COUNT = 10_000
WORKSPACE_ID = UUID("6cbd500f-f290-50cc-a964-57e3498c009a")
OWNER_TAB_ID = "symbol-stress-v3"
OUTPUT = Path(__file__).resolve().parent


def main() -> None:
    local = {f"local_symbol_{index:04d}": f"0x{index & 0xFFFF:04X}" for index in range(LOCAL_COUNT)}
    global_ = {f"global_symbol_{index:05d}": f"0x{index & 0xFFFF:04X}" for index in range(GLOBAL_COUNT)}
    _write_symbols("local_symbols_1500", local, SymbolScope.LOCAL, OWNER_TAB_ID)
    _write_symbols("global_symbols_10000", global_, SymbolScope.GLOBAL, None)
    (OUTPUT / "symbol_stress_11500_lines.asm").write_text(
        "\n".join(_assembly_lines()) + "\n",
        encoding="utf-8",
    )


def _assembly_lines() -> list[str]:
    lines = [
        "* virtual_memory_range 0x80000000 0x801FFFFF",
        "* import current_file 0x80000000",
        "* define $sp 0x801FFFF0",
        "* define $pc 0x80000000",
        "; Synthetic v3 stress source: 1,500 local + 10,000 global Symbols",
        "stress_start:",
    ]
    for index in range(LOCAL_COUNT):
        if index % 128 == 0:
            lines.extend((f"local_block_{index:04d}:", f"; local block {index // 128}"))
        lines.append(f"ori $t0, $zero, _local_symbol_{index:04d}")
    for index in range(GLOBAL_COUNT):
        if index % 256 == 0:
            lines.extend((f"global_block_{index:05d}:", f"; global block {index // 256}"))
        lines.append(f"ori $t1, $zero, @global_symbol_{index:05d}")
    lines.extend(("jr $ra", "nop"))
    return lines


def _write_symbols(
    name: str,
    values: dict[str, str],
    scope: SymbolScope,
    owner: str | None,
) -> None:
    definitions = tuple(
        LegacySymbolsPayloadAdapter(str(WORKSPACE_ID)).from_mapping(
            values,
            scope,
            owner,
        )
    )
    payload = {
        "schema_version": SYMBOL_SCHEMA_VERSION,
        "workspace_id": str(WORKSPACE_ID),
        "module_id": name,
        "name": name,
        "symbol_definitions": definitions_payload(definitions),
        "symbols": values,
    }
    with (OUTPUT / f"{name}.json").open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
