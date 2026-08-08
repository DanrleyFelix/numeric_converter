from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)


RECOVERY_ROW_THRESHOLD = 10_000
RECOVERY_SOURCE_BYTE_THRESHOLD = 256 * 1024


@dataclass(frozen=True)
class BinaryWorkbenchRecoveryPlan:
    """Describe a potentially expensive initial tab materialization."""

    suspected_tab_id: str
    row_counts: dict[str, int]


def recovery_plan(
    state: BinaryWorkbenchStateDTO,
) -> BinaryWorkbenchRecoveryPlan | None:
    """Return a preflight plan before an uninterruptible Qt projection begins."""

    counts = {tab.tab_id: _materialized_row_count(tab) for tab in state.tabs}
    if not counts:
        return None
    active = next(
        (tab for tab in state.tabs if tab.tab_id == state.active_tab_id),
        None,
    )
    if active is None:
        return None
    active_count = counts.get(active.tab_id, 0)
    if active_count < RECOVERY_ROW_THRESHOLD and not _has_large_source(active):
        return None
    return BinaryWorkbenchRecoveryPlan(active.tab_id, counts)


def selected_recovery_state(
    state: BinaryWorkbenchStateDTO,
    excluded_tab_ids: set[str],
    *,
    preserve_excluded: bool = True,
) -> tuple[BinaryWorkbenchStateDTO, tuple[BinaryWorkbenchTabContextDTO, ...]]:
    """Create a light startup state and optionally retain omitted payloads."""

    if not preserve_excluded:
        # Blank project is a real replacement, not the old heavy workspace
        # with only its visible tabs removed.  In particular, do not eagerly
        # carry a large Global Symbols catalog into an explicitly blank start.
        return BinaryWorkbenchStateDTO(), ()

    tabs = [tab for tab in state.tabs if tab.tab_id not in excluded_tab_ids]
    omitted = (
        tuple(tab for tab in state.tabs if tab.tab_id in excluded_tab_ids)
        if preserve_excluded
        else ()
    )
    active = state.active_tab_id if any(tab.tab_id == state.active_tab_id for tab in tabs) else None
    if active is None and tabs:
        active = tabs[0].tab_id
    return replace(state, tabs=tabs, active_tab_id=active), omitted


def merge_recovery_tabs(
    state: BinaryWorkbenchStateDTO,
    omitted: tuple[BinaryWorkbenchTabContextDTO, ...],
) -> BinaryWorkbenchStateDTO:
    """Preserve skipped recovery data without materializing it in the window."""

    visible_ids = {tab.tab_id for tab in state.tabs}
    retained = [tab for tab in omitted if tab.tab_id not in visible_ids]
    return replace(state, tabs=[*state.tabs, *retained])


def _materialized_row_count(tab: BinaryWorkbenchTabContextDTO) -> int:
    version_rows = max((len(version.rows) for version in tab.versions), default=0)
    return max(len(tab.rows), len(tab.original_rows), version_rows)


def _has_large_source(tab: BinaryWorkbenchTabContextDTO) -> bool:
    """Detect a costly source without reading or materializing its contents."""

    if not tab.source_path:
        return False
    try:
        return Path(tab.source_path).stat().st_size >= RECOVERY_SOURCE_BYTE_THRESHOLD
    except OSError:
        return False
