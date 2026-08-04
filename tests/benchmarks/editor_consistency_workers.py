"""Controlled 4 KB benchmark used to select the consistency worker count.

Run manually with:
    python tests/benchmarks/editor_consistency_workers.py
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.binary_workbench.codec_registry import binary_workbench_worker_codec_for
from src.core.binary_workbench.editor_consistency import DirtyRange, EditorOwner, SemanticSnapshot
from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.distribution import (
    LineContributionIndex,
    iter_offset_batches,
)
from src.core.binary_workbench.editor_consistency.semantic import calculate_semantic_result


SAMPLES = 9
LINE_COUNT = 1024


def _lines() -> tuple[str, ...]:
    return tuple(
        f"label_{index}: addiu $t0, $t0, 1"
        if index % 8 == 0
        else f"bne $t0, $zero, label_{index - 7}"
        if index % 8 == 7
        else "nop"
        for index in range(LINE_COUNT)
    )


def main() -> None:
    owner = EditorOwner("benchmark", "4kb-many-labels", 1)
    lines = _lines()
    contributions = LineContributionIndex([4] * LINE_COUNT).snapshot()

    def visual() -> float:
        started = perf_counter()
        tuple(
            iter_offset_batches(
                snapshot=contributions,
                owner=owner,
                structural_revision=1,
                generation=1,
                offset_names=("File", "Reference Offset A"),
                offset_bases={"Reference Offset A": "0x80000000"},
                dirty_ranges=(DirtyRange(0, LINE_COUNT - 1),),
                dirty_from_line=0,
                viewport=DirtyRange(480, 544),
                token=CancellationToken(),
            )
        )
        return (perf_counter() - started) * 1000

    def semantic():
        return calculate_semantic_result(
            SemanticSnapshot(
                owner,
                1,
                1,
                "PSX - Mips R3000A",
                binary_workbench_worker_codec_for("PSX - Mips R3000A"),
                lines,
                ("File",),
                {},
                {},
                {},
            ),
            CancellationToken(),
        )

    alone = [visual() for _ in range(SAMPLES)]
    concurrent = []
    for _ in range(SAMPLES):
        with ThreadPoolExecutor(max_workers=2) as pool:
            semantic_future = pool.submit(semantic)
            visual_future = pool.submit(visual)
            concurrent.append(visual_future.result())
            semantic_future.result()

    alone_median = median(alone)
    concurrent_median = median(concurrent)
    delta = ((concurrent_median / alone_median) - 1) * 100
    selected = 2 if delta <= 10 else 1
    print(f"visual_alone_ms={alone_median:.4f}")
    print(f"visual_with_two_workers_ms={concurrent_median:.4f}")
    print(f"visual_latency_delta_percent={delta:.2f}")
    print(f"selected_worker_count={selected}")


if __name__ == "__main__":
    main()
