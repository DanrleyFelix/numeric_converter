"""Measure real Qt costs for the large Assembly/Symbol fixture.

Run with ``QT_QPA_PLATFORM=offscreen python -m
tests.benchmarks.binary_workbench_ui_stress_benchmark`` from the repository root.
"""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import statistics
import sys
from time import perf_counter

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QWidget

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchStateDTO,
)
from src.core.binary_workbench.editor_consistency.classification.service import (
    declared_label,
)
from src.presentation.ui.components.binary_workbench.editor.page import (
    BinaryWorkbenchEditorPage,
)
from src.presentation.ui.components.binary_workbench.tabs.tab_context_factory import (
    create_assembly_tab,
    create_scratch_tab,
)

FIXTURE = ROOT / "examples" / "symbol_stress_v3"
SOURCE = FIXTURE / "symbol_stress_11500_lines.asm"
LOCAL = FIXTURE / "local_symbols_1500.json"
GLOBAL = FIXTURE / "global_symbols_10000.json"
def _milliseconds(action):
    started = perf_counter()
    value = action()
    return (perf_counter() - started) * 1000.0, value


def _symbols(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("symbols", "variables", "equates"):
        if isinstance(payload.get(key), dict):
            return dict(payload[key])
    return {}


def _rss_mib() -> float | None:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return None


def _page(context) -> BinaryWorkbenchEditorPage:
    page = BinaryWorkbenchEditorPage(context)
    page.resize(1280, 800)
    page.show()
    QApplication.processEvents()
    return page


def _open_case(
    state,
    variables,
    equates,
) -> tuple[float, float, float, BinaryWorkbenchEditorPage]:
    """Separate source derivation from Qt projection during startup."""

    started = perf_counter()
    context = create_assembly_tab(state, SOURCE)
    context = replace(context, variables=variables, equates=equates)
    context_ms = (perf_counter() - started) * 1000.0
    page_started = perf_counter()
    page = _page(context)
    page.grid.set_edit_rules(BinaryWorkbenchEditRulesDTO(allow_byte_shift=True))
    page_ms = (perf_counter() - page_started) * 1000.0
    return (perf_counter() - started) * 1000.0, context_ms, page_ms, page


def _assembly_backspace_case(page: BinaryWorkbenchEditorPage) -> tuple[float, float]:
    """Measure edits inside the already materialized viewport."""

    editor = page.grid.instructions
    block = _first_visible_assembled_block(page)
    if not block.isValid() or not block.text().strip():
        raise RuntimeError("The benchmark viewport has no editable Assembly row.")
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    editor.setTextCursor(cursor)
    samples: list[float] = []
    while block.text():
        started = perf_counter()
        QTest.keyClick(editor, Qt.Key_Backspace)
        QApplication.processEvents()
        samples.append((perf_counter() - started) * 1000.0)
        block = editor.document().findBlockByNumber(block.blockNumber())
    return samples[0], max(samples[1:], default=0.0)


def _bytes_backspace_case(
    page: BinaryWorkbenchEditorPage,
) -> tuple[float | None, float | None, float | None]:
    """Measure character deletion and the structural empty-row transition."""

    QTest.qWait(90)
    editor = page.grid.bytes
    block = editor.firstVisibleBlock()
    remaining = 80
    while block.isValid() and remaining and not block.text().strip():
        block = block.next()
        remaining -= 1
    if not block.isValid() or not block.text().strip():
        # An unresolved-symbol control case intentionally has no assembled
        # Bytes. Opening and scrolling are still valid measurements.
        return None, None, None
    block_number = block.blockNumber()
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    editor.setTextCursor(cursor)
    character_samples: list[float] = []
    while block.text():
        started = perf_counter()
        QTest.keyClick(editor, Qt.Key_Backspace)
        QApplication.processEvents()
        elapsed = (perf_counter() - started) * 1000.0
        character_samples.append(elapsed)
        block = editor.document().findBlockByNumber(block_number)
    started = perf_counter()
    QTest.keyClick(editor, Qt.Key_Backspace)
    QApplication.processEvents()
    row_delete = (perf_counter() - started) * 1000.0
    profiler = None
    if os.environ.get("BWB_PROFILE_BYTES_UNDO"):
        import cProfile

        profiler = cProfile.Profile()
        profiler.enable()
    started = perf_counter()
    QTest.keyClick(editor, Qt.Key_Z, Qt.ControlModifier)
    QApplication.processEvents()
    undo = (perf_counter() - started) * 1000.0
    if profiler is not None:
        import pstats

        profiler.disable()
        pstats.Stats(profiler).sort_stats("cumulative").print_stats(35)
    return max(character_samples, default=0.0), row_delete, undo


def _assembly_row_delete_case(page: BinaryWorkbenchEditorPage) -> float:
    """Measure one accepted structural row removal in the Assembly source."""

    editor = page.grid.instructions
    block = _first_visible_assembled_block(page, require_next=True)
    if not block.isValid() or not block.next().isValid():
        return 0.0
    cursor = QTextCursor(editor.document())
    cursor.setPosition(block.position())
    cursor.setPosition(block.next().position(), QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    profiler = None
    if os.environ.get("BWB_PROFILE_ROW_DELETE"):
        import cProfile

        profiler = cProfile.Profile()
        profiler.enable()
    started = perf_counter()
    QTest.keyClick(editor, Qt.Key_Backspace)
    QApplication.processEvents()
    elapsed = (perf_counter() - started) * 1000.0
    if profiler is not None:
        import pstats

        profiler.disable()
        pstats.Stats(profiler).sort_stats("cumulative").print_stats(35)
    return elapsed


def _first_visible_assembled_block(
    page: BinaryWorkbenchEditorPage,
    *,
    require_next: bool = False,
):
    """Find ordinary assembled code, excluding directives and label-only rows."""

    editor = page.grid.instructions
    block = editor.firstVisibleBlock()
    remaining = 160
    while block.isValid() and remaining:
        index = block.blockNumber()
        text = block.text()
        current_valid = (
            0 <= index < len(page.grid._rows)
            and bool(page.grid._codec.instruction_code(text))
            and not declared_label(text)
        )
        next_valid = (
            not require_next
            or (
                index + 1 < len(page.grid._rows)
                and bool(page.grid._codec.instruction_code(block.next().text()))
                and not declared_label(block.next().text())
            )
        )
        if current_valid and next_valid:
            return block
        block = block.next()
        remaining -= 1
    return block


def _scroll_case(page: BinaryWorkbenchEditorPage) -> tuple[float, float]:
    scrollbar = page.grid.scrollbar
    target = max(scrollbar.minimum(), scrollbar.maximum() // 2)
    started = perf_counter()
    scrollbar.setValue(target)
    # Include the 16 ms frame coalescer and the actual viewport projection.
    QTest.qWait(20)
    cold = (perf_counter() - started) * 1000.0
    QApplication.processEvents()
    warm, _ = _milliseconds(lambda: scrollbar.setValue(target))
    return cold, warm


def _paste_case(state, source_text: str) -> float:
    page = _page(create_scratch_tab(state))
    started = perf_counter()
    page.grid.instructions.setPlainText(source_text)
    QApplication.processEvents()
    elapsed = (perf_counter() - started) * 1000.0
    page.close()
    page.deleteLater()
    QApplication.processEvents()
    return elapsed


def main() -> None:
    app = QApplication.instance() or QApplication([])
    state = BinaryWorkbenchStateDTO()
    local = _symbols(LOCAL)
    global_ = _symbols(GLOBAL)
    effective = {**global_, **local}
    source_text = SOURCE.read_text(encoding="utf-8")
    cases = (
        ("no_symbols", {}, {}),
        ("global_symbols", global_, global_),
        ("local_and_global", effective, effective),
    )
    selected = {item for item in sys.argv[1:] if not item.startswith("--")}
    if selected:
        cases = tuple(case for case in cases if case[0] in selected)
    run_count = 1 if selected else 3
    runs: dict[str, list[dict[str, float | None]]] = {}
    for name, variables, equates in cases:
        values = []
        for run in range(run_count):
            print(f"running {name} {run + 1}/{run_count}", file=sys.stderr, flush=True)
            before = _rss_mib()
            open_ms, source_derivation_ms, qt_projection_ms, page = _open_case(
                state,
                variables,
                equates,
            )
            cold_scroll_ms, cached_scroll_ms = _scroll_case(page)
            page.grid.set_edit_rules(
                BinaryWorkbenchEditRulesDTO(allow_byte_shift=False)
            )
            assembly_locked_first_delete_ms, assembly_locked_quiet_delete_max_ms = (
                _assembly_backspace_case(page)
            )
            page.grid.set_edit_rules(
                BinaryWorkbenchEditRulesDTO(allow_byte_shift=True)
            )
            assembly_first_delete_ms, assembly_quiet_delete_max_ms = (
                _assembly_backspace_case(page)
            )
            assembly_row_delete_ms = _assembly_row_delete_case(page)
            (
                bytes_character_delete_max_ms,
                bytes_row_delete_ms,
                bytes_undo_row_ms,
            ) = (
                _bytes_backspace_case(page)
            )
            after = _rss_mib()
            values.append(
                {
                    "open_ms": open_ms,
                    "source_derivation_ms": source_derivation_ms,
                    "qt_projection_ms": qt_projection_ms,
                    "cold_scroll_ms": cold_scroll_ms,
                    "cached_scroll_ms": cached_scroll_ms,
                    "assembly_locked_first_delete_ms": assembly_locked_first_delete_ms,
                    "assembly_locked_quiet_delete_max_ms": assembly_locked_quiet_delete_max_ms,
                    "assembly_first_delete_ms": assembly_first_delete_ms,
                    "assembly_quiet_delete_max_ms": assembly_quiet_delete_max_ms,
                    "assembly_row_delete_ms": assembly_row_delete_ms,
                    "bytes_character_delete_max_ms": bytes_character_delete_max_ms,
                    "bytes_row_delete_ms": bytes_row_delete_ms,
                    "bytes_undo_row_ms": bytes_undo_row_ms,
                    "rss_delta_mib": (
                        None if before is None or after is None else after - before
                    ),
                    "widget_count": len(page.findChildren(QWidget)),
                    "text_editor_count": len(page.findChildren(QPlainTextEdit)),
                    "text_block_count": sum(
                        editor.document().blockCount()
                        for editor in page.findChildren(QPlainTextEdit)
                    ),
                }
            )
            page.close()
            page.deleteLater()
            QApplication.processEvents()
        runs[name] = values
    paste = [_paste_case(state, source_text) for _ in range(run_count)]
    summary = {
        name: {
            metric: (
                statistics.median(samples)
                if (
                    samples := [
                        value[metric]
                        for value in values
                        if value[metric] is not None
                    ]
                )
                else None
            )
            for metric in values[0]
        }
        for name, values in runs.items()
    }
    summary["paste_without_symbols"] = {"median_ms": statistics.median(paste)}
    print(
        json.dumps(
            {
                "dataset": {
                    "source_lines": len(source_text.splitlines()),
                    "source_bytes": len(source_text.encode("utf-8")),
                    "local_symbols": len(local),
                    "global_symbols": len(global_),
                },
                "runs_per_case": run_count,
                "summary": summary,
                "raw": runs,
                "paste_raw_ms": paste,
            },
            indent=2,
        )
    )
    app.processEvents()


if __name__ == "__main__":
    main()
