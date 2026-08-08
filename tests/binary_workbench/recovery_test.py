from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchRowDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.tabs.recovery import (
    RECOVERY_ROW_THRESHOLD,
    RECOVERY_SOURCE_BYTE_THRESHOLD,
    merge_recovery_tabs,
    recovery_plan,
    selected_recovery_state,
)


def _tab(tab_id: str, rows: int) -> BinaryWorkbenchTabContextDTO:
    return BinaryWorkbenchTabContextDTO(
        tab_id=tab_id,
        kind="assembly",
        display_name=f"{tab_id}.asm",
        rows=[BinaryWorkbenchRowDTO() for _ in range(rows)],
    )


def test_recovery_preflight_only_flags_a_heavy_active_tab():
    inactive_heavy = _tab("inactive", RECOVERY_ROW_THRESHOLD + 1)
    active_light = _tab("active", 2)
    state = BinaryWorkbenchStateDTO(
        tabs=[inactive_heavy, active_light],
        active_tab_id="active",
    )

    assert recovery_plan(state) is None

    state = BinaryWorkbenchStateDTO(
        tabs=[active_light, inactive_heavy],
        active_tab_id="inactive",
    )
    plan = recovery_plan(state)

    assert plan is not None
    assert plan.suspected_tab_id == "inactive"


def test_recovery_exclusions_remain_available_for_safe_persistence():
    first = _tab("first", 1)
    second = _tab("second", 2)
    state = BinaryWorkbenchStateDTO(
        tabs=[first, second],
        active_tab_id="second",
    )

    selected, omitted = selected_recovery_state(state, {"second"})
    restored = merge_recovery_tabs(selected, omitted)

    assert [tab.tab_id for tab in selected.tabs] == ["first"]
    assert selected.active_tab_id == "first"
    assert [tab.tab_id for tab in omitted] == ["second"]
    assert {tab.tab_id for tab in restored.tabs} == {"first", "second"}


def test_blank_recovery_discards_old_tabs_instead_of_merging_them_back():
    """A blank startup must replace the persisted heavy-tab selection."""

    old = _tab("old", 2)
    state = BinaryWorkbenchStateDTO(
        tabs=[old],
        active_tab_id="old",
        global_symbols={"heavy": "0x1"},
    )

    selected, omitted = selected_recovery_state(
        state,
        {"old"},
        preserve_excluded=False,
    )

    assert selected.tabs == []
    assert selected.active_tab_id is None
    assert selected.global_symbols == {}
    assert omitted == ()


def test_recovery_preflight_detects_a_large_source_without_materialized_rows(tmp_path):
    source = tmp_path / "large.asm"
    source.write_bytes(b" " * RECOVERY_SOURCE_BYTE_THRESHOLD)
    active = BinaryWorkbenchTabContextDTO(
        tab_id="active",
        kind="assembly",
        display_name="large.asm",
        source_path=str(source),
    )
    state = BinaryWorkbenchStateDTO(tabs=[active], active_tab_id="active")

    plan = recovery_plan(state)

    assert plan is not None
    assert plan.suspected_tab_id == "active"
    assert plan.row_counts == {"active": 0}
