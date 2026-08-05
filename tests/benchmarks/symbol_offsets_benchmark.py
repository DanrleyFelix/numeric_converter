from __future__ import annotations

import gc
import json
import math
from pathlib import Path
import statistics
import sys
from time import perf_counter
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.binary_workbench.symbols import (
    GlobalSymbolRepository,
    InstructionLayoutIndex,
    LocalSymbolRepository,
    SymbolOccurrenceIndex,
    SymbolQueryService,
)
from src.core.binary_workbench.symbols.runtime import _matching_source_lines

LOCAL_COUNT = 1_500
GLOBAL_COUNT = 10_000
OCCURRENCES_PER_SYMBOL = 30


def _dataset() -> tuple[dict[str, str], dict[str, str], tuple[tuple[str, str], ...]]:
    local = {f"local_{index}": hex(index) for index in range(LOCAL_COUNT)}
    global_ = {f"global_{index}": hex(index) for index in range(GLOBAL_COUNT)}
    lines: list[tuple[str, str]] = []
    position = 0
    for name in (*local, *global_):
        for _ in range(OCCURRENCES_PER_SYMBOL):
            lines.append((f"i{position}", f"addiu $v0, $zero, _{name}"))
            position += 1
    return local, global_, tuple(lines)


def _milliseconds(action):
    started = perf_counter()
    value = action()
    return (perf_counter() - started) * 1000.0, value


def _run_once(local, global_, lines, workspace_id):
    globals_repo = GlobalSymbolRepository(workspace_id)
    locals_repo = LocalSymbolRepository(workspace_id)
    definitions_ms, _ = _milliseconds(lambda: (
        globals_repo.replace_all(global_),
        locals_repo.for_tab("tab").replace_all(local),
    ))
    resolver = SymbolQueryService(globals_repo, locals_repo).snapshot("tab")
    occurrences = SymbolOccurrenceIndex("tab")
    index_ms, _ = _milliseconds(lambda: occurrences.rebuild(lines, resolver))
    search_snapshot_ms, search_text = _milliseconds(
        lambda: "\n".join(text for _instruction_id, text in lines).casefold()
    )
    lazy_query_ms, lazy_matches = _milliseconds(
        lambda: _matching_source_lines(search_text, "global_0")
    )
    ids = tuple(item[0] for item in lines)
    layout_ms, layout = _milliseconds(
        lambda: InstructionLayoutIndex(
            ids,
            (4,) * len(ids),
            sequential_id_prefix="i",
            sequential_id_base=10,
        )
    )
    first_base_ms, _ = _milliseconds(lambda: layout.set_base(0x1000))
    second_base_ms, _ = _milliseconds(lambda: layout.set_base(0x2000))
    definition = resolver.resolve("global_0")
    query_ms, offsets = _milliseconds(
        lambda: layout.offsets_for(definition.symbol_id, occurrences) if definition else ()
    )
    cold_scroll_ms, cached = _milliseconds(
        lambda: tuple(layout.offset_for(item) for item in ids[100_000:100_096])
    )
    warm_scroll_ms, _ = _milliseconds(lambda: cached)
    paste_ms, _ = _milliseconds(
        lambda: layout.splice(100, 0, ((f"paste{index}", 4) for index in range(2_000)))
    )
    undo_ms, _ = _milliseconds(lambda: layout.splice(100, 2_000, ()))
    last_ms, last_offset = _milliseconds(lambda: layout.append("last", 4))
    return {
        "full_build_ms": definitions_ms + index_ms + layout_ms,
        "definitions_ms": definitions_ms,
        "index_ms": index_ms,
        "search_snapshot_ms": search_snapshot_ms,
        "lazy_query_30_occurrences_ms": lazy_query_ms,
        "layout_ms": layout_ms,
        "first_offset_change_ms": first_base_ms,
        "second_offset_change_ms": second_base_ms,
        "query_30_offsets_ms": query_ms,
        "cold_scroll_96_lines_ms": cold_scroll_ms,
        "cached_scroll_ms": warm_scroll_ms,
        "paste_2000_ms": paste_ms,
        "undo_2000_ms": undo_ms,
        "last_offset_insert_ms": last_ms,
        "queried_offsets": len(offsets),
        "lazy_matches": len(lazy_matches),
        "last_offset": last_offset,
    }


def _summary(values):
    ordered = sorted(values)
    return {
        "median_ms": statistics.median(ordered),
        "p95_ms": ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)],
        "max_ms": max(ordered),
    }


def main() -> None:
    local, global_, lines = _dataset()
    runs = []
    workspace_id = str(uuid4())
    for _ in range(3):
        runs.append(_run_once(local, global_, lines, str(uuid4())))
        gc.collect()
    for _ in range(5):
        runs.append(_run_once(local, global_, lines, workspace_id))
        gc.collect()
    metrics = {
        key: _summary([run[key] for run in runs])
        for key in runs[0]
        if key.endswith("_ms")
    }
    memory = {}
    try:
        import psutil

        info = psutil.Process().memory_info()
        memory = {
            "rss_mib": info.rss / (1024 * 1024),
            "peak_mib": getattr(info, "peak_wset", info.rss) / (1024 * 1024),
        }
    except ImportError:
        memory = {"rss_mib": None, "peak_mib": None}
    print(json.dumps({
        "dataset": {
            "local_symbols": LOCAL_COUNT,
            "global_symbols": GLOBAL_COUNT,
            "occurrences_per_symbol": OCCURRENCES_PER_SYMBOL,
            "occurrences": len(lines),
        },
        "runs": {"cold": 3, "warm": 5},
        "metrics": metrics,
        "memory": memory,
        "jobs": 0,
        "events_per_logical_operation": 1,
        "repaints": 0,
        "maximum_batch_size": 256,
    }, indent=2))


if __name__ == "__main__":
    main()
