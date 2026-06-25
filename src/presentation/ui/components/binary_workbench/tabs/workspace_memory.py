from __future__ import annotations

from dataclasses import replace

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO

WORKSPACE_HEAVY_TAB_LIMIT = 5


def unloadable_workspace_context(context: BinaryWorkbenchTabContextDTO) -> bool:
    if context.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL:
        return False
    return context.kind == BINARY_WORKBENCH_TAB_KIND.BINARY or bool(context.workspace_path)


def workspace_heavy_context_loaded(context: BinaryWorkbenchTabContextDTO) -> bool:
    return any(
        (
            context.labels,
            context.variables,
            context.equates,
            context.symbol_offsets,
            context.search_cache,
            context.versions,
            context.offset_regions,
            context.kind in {
                BINARY_WORKBENCH_TAB_KIND.BINARY,
                BINARY_WORKBENCH_TAB_KIND.INTERNAL,
            }
            and (context.rows or context.byte_overlays or context.instruction_overlays),
        )
    )


def workspace_heavy_context_unloaded(context: BinaryWorkbenchTabContextDTO) -> bool:
    return (
        unloadable_workspace_context(context)
        and bool(context.workspace_path)
        and not workspace_heavy_context_loaded(context)
    )


def unload_workspace_heavy_context(
    context: BinaryWorkbenchTabContextDTO,
) -> BinaryWorkbenchTabContextDTO:
    updates = {
        "labels": {},
        "variables": {},
        "equates": {},
        "symbol_offsets": {},
        "search_cache": {},
        "versions": [],
        "offset_regions": [],
    }
    if context.kind in {
        BINARY_WORKBENCH_TAB_KIND.BINARY,
        BINARY_WORKBENCH_TAB_KIND.INTERNAL,
    }:
        updates.update(
            rows=[],
            byte_overlays={},
            instruction_overlays={},
            version_dirty=False,
        )
    return replace(context, **updates)
