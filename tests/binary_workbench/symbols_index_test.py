from uuid import uuid4

import pytest

from src.core.binary_workbench.editor_consistency.distribution import RangeConsistencyIndex
from src.core.binary_workbench.symbols import (
    GlobalSymbolRepository,
    InstructionLayoutIndex,
    LegacySymbolsPayloadAdapter,
    LocalSymbolRepository,
    ProcessingClass,
    SymbolOccurrenceIndex,
    SymbolQueryService,
    SymbolRuntime,
    SymbolScope,
    SymbolWorkItem,
    SymbolWorkScheduler,
    WorkPriority,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.repository.binary_workbench_payload import (
    binary_workbench_state_from_payload,
    binary_workbench_state_to_payload,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets


def test_legacy_fields_share_one_definition_collection_with_documented_precedence():
    adapter = LegacySymbolsPayloadAdapter(str(uuid4()))
    result = adapter.adapt(
        {
            "variables": {"shared": "1", "variable": "2"},
            "equates": {"shared": "3", "equate": "4"},
            "symbols": {"shared": "5", "symbol": "6"},
        },
        SymbolScope.LOCAL,
        "tab",
    )

    assert {item.name: item.value for item in result.definitions} == {
        "variable": "2",
        "equate": "4",
        "shared": "5",
        "symbol": "6",
    }
    assert result.legacy_detected is True


def test_mapping_adapter_preserves_identity_for_one_logical_rename():
    repository = GlobalSymbolRepository(str(uuid4()))
    repository.replace_all({"before": "1", "untouched": "2"})
    original = repository.resolve("before")

    repository.replace_all({"after": "3", "untouched": "2"})

    renamed = repository.resolve("after")
    assert original is not None and renamed is not None
    assert renamed.symbol_id == original.symbol_id
    assert renamed.value == "3"


def test_modern_definitions_warn_when_legacy_mirror_diverges():
    workspace_id = str(uuid4())
    definition = next(LegacySymbolsPayloadAdapter(workspace_id).from_mapping(
        {"authoritative": "1"},
        SymbolScope.GLOBAL,
    ))
    adapted = LegacySymbolsPayloadAdapter(workspace_id).adapt(
        {
            "global_symbol_definitions": [{
                "symbol_id": definition.symbol_id,
                "name": definition.name,
                "value": definition.value,
            }],
            "global_symbols": {"authoritative": "2"},
        },
        SymbolScope.GLOBAL,
        modern_key="global_symbol_definitions",
    )

    assert {item.name: item.value for item in adapted.definitions} == {
        "authoritative": "1"
    }
    assert adapted.conflicts == (
        "global_symbols differs from authoritative global_symbol_definitions.",
    )


def test_occurrences_resolve_aliases_and_offsets_follow_lazy_base_changes():
    workspace_id = str(uuid4())
    globals_ = GlobalSymbolRepository(workspace_id)
    locals_ = LocalSymbolRepository(workspace_id)
    globals_.replace_all({"shared": "0x10"})
    locals_.for_tab("tab").replace_all({"local": "0x20", "shared": "0x30"})
    snapshot = SymbolQueryService(globals_, locals_).snapshot("tab")
    local_shared = snapshot.resolve("@shared")
    assert local_shared is not None and local_shared.value == "0x30"

    occurrences = SymbolOccurrenceIndex("tab")
    occurrences.rebuild(
        (("i0", "addiu $v0, $zero, _shared"), ("i1", "lui $v0, @local")),
        snapshot,
    )
    layout = InstructionLayoutIndex(("i0", "i1"), (4, 4), 0x100)

    assert layout.offsets_for(local_shared.symbol_id, occurrences) == (0x100,)
    layout.set_base(0x200)
    assert layout.offsets_for(local_shared.symbol_id, occurrences) == (0x200,)
    assert layout.append("i2", 4) == 0x208


def test_sequential_layout_splices_keep_offsets_without_global_position_rebuild():
    layout = InstructionLayoutIndex(
        ("tab:0", "tab:1", "tab:2"),
        (4, 4, 4),
        0x100,
        sequential_id_prefix="tab:",
        sequential_id_base=16,
    )

    layout.splice(1, 0, (("tab:3", 4), ("tab:4", 4)))
    assert layout.offset_for("tab:3") == 0x104
    assert layout.offset_for("tab:1") == 0x10C
    assert layout.offset_for("tab:2") == 0x110

    layout.splice(1, 2, ())
    assert layout.offset_for("tab:3") is None
    assert layout.offset_for("tab:1") == 0x104
    assert layout.append("tab:5", 4) == 0x10C
    assert layout.offset_for("tab:5") == 0x10C


def test_single_resolved_occurrence_is_found_after_an_unresolved_token():
    workspace_id = str(uuid4())
    globals_ = GlobalSymbolRepository(workspace_id)
    locals_ = LocalSymbolRepository(workspace_id)
    globals_.replace_all({"known": "0x10"})
    snapshot = SymbolQueryService(globals_, locals_).snapshot("tab")
    occurrences = SymbolOccurrenceIndex("tab")

    occurrences.rebuild(
        (("i0", "addiu $v0, _missing, @known"),),
        snapshot,
    )

    stored = occurrences.occurrences_for_instruction("i0")
    assert len(stored) == 1
    assert stored[0].tab_id == "tab"
    assert stored[0].operand_index == 1
    assert stored[0].occurrence_id == "i0"


def test_symbol_runtime_does_not_materialize_unrequested_tabs():
    runtime = SymbolRuntime(str(uuid4()))
    runtime.set_global_definitions({"global": "1"})
    runtime.set_local_definitions("inactive", {"local": "2"})

    assert runtime.is_materialized("inactive") is False
    runtime.materialize_tab(
        "active",
        [BinaryWorkbenchRowDTO({"File": "0x00000000"}, "nop", "00 00 00 00")],
        {},
    )
    assert runtime.is_materialized("active") is True
    assert runtime.is_materialized("inactive") is False


def test_cold_symbol_query_indexes_only_the_requested_name():
    runtime = SymbolRuntime(str(uuid4()))
    runtime.set_global_definitions({"target": "1", "other": "2"})
    rows = [
        BinaryWorkbenchRowDTO({"File": f"0x{index * 4:08X}"}, instruction, "00 00 00 00")
        for index, instruction in enumerate((
            "nop",
            "addiu $v0, $zero, _other",
            "addiu $v0, $zero, @target",
        ))
    ]
    runtime.materialize_tab("tab", rows, {}, initial_range=(0, 0))

    assert runtime.offsets_for("tab", "target") == ["0x00000008"]


def test_inactive_legacy_tab_payload_is_copied_without_materializing_symbols():
    payload = {
        "active_tab_id": "one",
        "tabs": [
            {"tab_id": "one", "kind": "scratch", "display_name": "one", "symbols": {"a": "1"}},
            {"tab_id": "two", "kind": "scratch", "display_name": "two", "variables": {"b": "2"}},
        ],
    }

    state = binary_workbench_state_from_payload(payload)
    assert state.tabs[0].symbols == {"a": "1"}
    assert state.tabs[1].symbols == {}
    assert state.tabs[1].lazy_symbol_payload["variables"] == {"b": "2"}
    stored = binary_workbench_state_to_payload(state)
    assert stored["tabs"][1]["variables"] == {"b": "2"}


def test_offset_scan_is_linear_in_tokens_and_keeps_label_addresses():
    rows = [
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, "lui $v0, @alpha", "00 00 00 00"),
        BinaryWorkbenchRowDTO({"File": "0x00000004"}, "addiu $v0, $v0, _beta", "00 00 00 00"),
    ]

    assert symbol_offsets(rows, {"alpha": "1", "beta": "2"}, {}, {"label": "0x8"}) == {
        "alpha": ["0x00000000"],
        "beta": ["0x00000004"],
        "label": ["0x8"],
    }


def test_range_cache_and_scheduler_enforce_zero_work_and_extraordinary_reason():
    ranges = RangeConsistencyIndex()
    ranges.reset(100, 3)
    assert ranges.is_current(20, 40, 3)
    ranges.invalidate_from(30, 100, 4)
    assert ranges.is_current(0, 29, 4)
    assert not ranges.is_current(30, 31, 4)
    ranges.mark((30, 31), 4)
    assert ranges.is_current(30, 31, 4)

    with pytest.raises(ValueError):
        SymbolWorkItem(
            WorkPriority.LATE_CACHE,
            0,
            0,
            0,
            ProcessingClass.EXTRAORDINARY,
        )
    scheduler = SymbolWorkScheduler()
    viewport = SymbolWorkItem(WorkPriority.VIEWPORT, 0, 10, 1)
    remainder = SymbolWorkItem(WorkPriority.ACTIVE_DIRTY_REMAINDER, 100, 0, 2)
    assert scheduler.order([remainder, viewport], 20)[0] == viewport
