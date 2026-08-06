from src.core.binary_workbench.codec_registry import binary_workbench_worker_codec_for
from src.core.binary_workbench.editor_consistency import (
    ChangeKind,
    DirtyRange,
    EditorOwner,
    SemanticSnapshot,
)
from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.classification import classify_line_change, merge_dirty_ranges
from src.core.binary_workbench.editor_consistency.distribution import (
    LineContributionIndex,
    build_offset_batches,
    incremental_offset_values,
)
from src.core.binary_workbench.editor_consistency.semantic import calculate_semantic_result


def test_contribution_index_reuses_untouched_immutable_segments():
    sizes = [4 if index % 3 else 0 for index in range(768)]
    index = LineContributionIndex(sizes)
    before = index.snapshot()

    index.splice(10, 1, [0])
    after = index.snapshot()

    assert after.chunks[1] is before.chunks[1]
    assert after.chunks[2] is before.chunks[2]
    assert index.prefix_bytes(500) == sum(sizes[:500]) - 4


def test_offset_batches_prioritize_viewport_margin_dirty_then_remainder():
    index = LineContributionIndex([4] * 500)
    token = CancellationToken()
    batches = build_offset_batches(
        index.snapshot(),
        EditorOwner("tab", "version", 1),
        2,
        3,
        ("File", "Reference Offset A"),
        {"Reference Offset A": "0x80000000"},
        (DirtyRange(300, 301),),
        300,
        DirtyRange(50, 60),
        token,
    )

    first_indices = [line for line, _offsets in batches[0].values]
    assert all(len(batch.values) <= 256 for batch in batches)
    assert first_indices[:11] == list(range(50, 61))
    assert first_indices[11:13] == [0, 1]
    assert first_indices[125:127] == [300, 301]
    offsets = dict(batches[0].values)
    assert offsets[300]["File"] == "0x000004B0"
    assert offsets[50]["Reference Offset A"] == "0x800000C8"


def test_cancelled_offset_job_does_not_produce_batches():
    token = CancellationToken()
    token.cancel()

    batches = build_offset_batches(
        LineContributionIndex([4] * 600).snapshot(),
        EditorOwner("tab", "version", 1),
        1,
        1,
        ("File",),
        {},
        (DirtyRange(0, 0),),
        0,
        DirtyRange(400, 450),
        token,
    )

    assert batches == ()


def test_incremental_offsets_only_distribute_preclassified_contributions():
    snapshot = LineContributionIndex([0, 4, 0, 4, 4]).snapshot()

    values = incremental_offset_values(
        snapshot,
        1,
        3,
        ("File", "ram"),
        {"ram": "0x80000000"},
    )

    assert values == (
        (1, {"File": "0x00000000", "ram": "0x80000000"}),
        (2, {"File": "-", "ram": "-"}),
        (3, {"File": "0x00000004", "ram": "0x80000004"}),
    )


def test_change_classification_and_dirty_range_coalescing():
    assert classify_line_change(4, 4).kind == ChangeKind.LOCAL
    assert classify_line_change(0, 0, label_changed=True).kind == ChangeKind.LOCAL_DEPENDENCY
    assert classify_line_change(4, 0).kind == ChangeKind.STRUCTURAL
    assert merge_dirty_ranges(
        (DirtyRange(20, 30), DirtyRange(50, 60)),
        DirtyRange(29, 52),
    ) == (DirtyRange(20, 60),)


def test_semantic_result_commits_labels_branches_and_hazards_as_one_revision():
    owner = EditorOwner("tab", "version", 4)
    snapshot = SemanticSnapshot(
        owner=owner,
        source_revision=12,
        generation=7,
        architecture="PSX - Mips R3000A",
        codec=binary_workbench_worker_codec_for("PSX - Mips R3000A"),
        lines=(
            "start: addiu $t0, $zero, 1",
            "beq $t0, $zero, end",
            "nop",
            "end: jr $ra",
        ),
        offset_names=("File",),
        offset_bases={},
        variables={},
        equates={},
    )

    result = calculate_semantic_result(snapshot, CancellationToken())

    assert result is not None
    assert (result.owner, result.source_revision, result.generation) == (owner, 12, 7)
    assert result.labels == {"start": "0x00000000", "end": "0x0000000C"}
    assert all(row.bytes_text for row in result.rows)
    assert result.rows[1].bytes_text != ""
