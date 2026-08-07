from __future__ import annotations

from contextlib import contextmanager

from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QTextCursor

from src.core.binary_workbench.encoding_tables import decode_hex_bytes
from src.core.binary_workbench.directive_folding import debugger_directive_fold_region
from src.core.binary_workbench.label_folding import label_fold_regions
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)


@contextmanager
def projection_transaction(
    grid,
    *,
    refresh_structure: bool = False,
    refresh_folding: bool = True,
    refresh_fold_offsets: bool = True,
    history_exclude: tuple = (),
    history_editors: tuple | None = None,
):
    """Apply one derived projection without exposing intermediate scroll states."""

    editors = list(_derived_editors(grid))
    excluded_ids = {id(editor) for editor in history_exclude}
    history_sources = (
        (*editors, grid.instructions)
        if history_editors is None
        else history_editors
    )
    tracked_editors = [
        editor
        for editor in dict.fromkeys(history_sources)
        if id(editor) not in excluded_ids
    ]
    for editor in tracked_editors:
        begin = getattr(editor, "begin_derived_projection", None)
        if begin is not None:
            begin()
    scrollbars = [grid.scrollbar, *(editor.verticalScrollBar() for editor in (*editors, grid.instructions))]
    blockers = [QSignalBlocker(item) for item in scrollbars]
    shared_value = grid.scrollbar.value()
    previous_updating = grid._updating
    grid._updating = True
    grid.setUpdatesEnabled(False)
    try:
        yield
        if refresh_structure:
            if refresh_folding:
                _refresh_fold_visibility(
                    grid,
                    render_offsets=refresh_fold_offsets,
                )
            grid._visible_start_offset = shared_value
            grid._configure_scrollbar()
            grid.scrollbar.setValue(min(shared_value, grid.scrollbar.maximum()))
        grid._scroll_static_document(grid.scrollbar.value())
    finally:
        for editor in reversed(tracked_editors):
            end = getattr(editor, "end_derived_projection", None)
            if end is not None:
                end()
        grid._updating = previous_updating
        grid.setUpdatesEnabled(True)
        del blockers
        grid.viewport().update() if hasattr(grid, "viewport") else grid.update()


def apply_structure_splice(
    grid,
    first: int,
    removed: int,
    inserted: list[BinaryWorkbenchRowDTO],
    *,
    refresh_folding: bool = True,
) -> None:
    """Splice every derived document while leaving Assembly text untouched."""

    editors = _derived_editors(grid)
    snapshots = _document_snapshots(editors)
    collapsed = set(grid._collapsed_labels)
    expected_before = max(1, len(grid._rows) - len(inserted) + removed)
    if any(editor.document().blockCount() != expected_before for editor in editors):
        _rebuild_derived_documents(grid)
        return
    try:
        with projection_transaction(
            grid,
            refresh_structure=True,
            refresh_folding=refresh_folding,
            refresh_fold_offsets=False,
            history_editors=editors,
        ):
            for name, editor in grid._offset_editors.items():
                _replace_span(
                    editor,
                    first,
                    removed,
                    [
                        grid._display_offset_row(first + offset, name, row.offsets.get(name, "-"))
                        for offset, row in enumerate(inserted)
                    ],
                )
                splice_overlays = getattr(editor, "splice_offset_blocks", None)
                if splice_overlays is not None:
                    splice_overlays(first, removed, len(inserted))
            if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.BYTES):
                _replace_span(
                    grid.bytes,
                    first,
                    removed,
                    [grid._display_bytes_row(row) for row in inserted],
                )
            if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.DECODED_TEXT):
                _replace_span(
                    grid.decoded_text,
                    first,
                    removed,
                    [grid._display_decoded_row(row) for row in inserted],
                )
            if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS):
                _replace_span(
                    grid.raw_instructions,
                    first,
                    removed,
                    [grid._display_raw_row(row) for row in inserted],
                )
            _validate_block_counts(grid)
        if not refresh_folding:
            grid._splice_cached_label_folding(first, removed, len(inserted))
    except Exception:
        grid._collapsed_labels = collapsed
        try:
            _rebuild_derived_documents(grid)
            return
        except Exception:
            if _snapshots_match_source(grid, snapshots):
                _restore_documents(grid, snapshots, refresh_structure=True)
            raise


def apply_bytes_structure_splice(
    grid,
    first: int,
    removed: int,
    inserted: list[BinaryWorkbenchRowDTO],
) -> None:
    """Splice Bytes-derived peers while leaving the edited Bytes text intact."""

    expected_before = max(1, len(grid._rows) - len(inserted) + removed)
    peers = (
        *grid._offset_editors.values(),
        *(
            (grid.raw_instructions,)
            if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS)
            else ()
        ),
        *(
            (grid.decoded_text,)
            if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.DECODED_TEXT)
            else ()
        ),
        grid.instructions,
    )
    if any(editor.document().blockCount() != expected_before for editor in peers):
        _rebuild_bytes_origin_projection(grid)
        return
    try:
        with projection_transaction(
            grid,
            refresh_structure=True,
            refresh_folding=False,
            refresh_fold_offsets=False,
            history_exclude=(grid.bytes,),
            history_editors=peers,
        ):
            for name, editor in grid._offset_editors.items():
                _replace_span(
                    editor,
                    first,
                    removed,
                    [
                        grid._display_offset_row(
                            first + offset,
                            name,
                            row.offsets.get(name, "-"),
                        )
                        for offset, row in enumerate(inserted)
                    ],
                )
                splice_overlays = getattr(editor, "splice_offset_blocks", None)
                if splice_overlays is not None:
                    splice_overlays(first, removed, len(inserted))
            if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS):
                _replace_span(
                    grid.raw_instructions,
                    first,
                    removed,
                    [grid._display_raw_row(row) for row in inserted],
                )
            if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.DECODED_TEXT):
                _replace_span(
                    grid.decoded_text,
                    first,
                    removed,
                    [grid._display_decoded_row(row) for row in inserted],
                )
            _replace_span(
                grid.instructions,
                first,
                removed,
                [grid._display_instruction(row.instruction) for row in inserted],
            )
            _validate_block_counts(grid)
        grid._splice_cached_label_folding(first, removed, len(inserted))
    except Exception:
        _rebuild_bytes_origin_projection(grid)


def apply_offset_values(grid, values: tuple[tuple[int, dict[str, str]], ...]) -> None:
    """Patch only offset documents for one structural revision batch."""

    editors = tuple(grid._offset_editors.values())
    snapshots = _line_snapshots(editors, tuple(index for index, _ in values))
    try:
        with projection_transaction(grid, history_editors=editors):
            for index, offsets in values:
                for name, editor in grid._offset_editors.items():
                    _replace_line(
                        editor,
                        index,
                        grid._display_offset_row(
                            index,
                            name,
                            offsets.get(name, "-"),
                        ),
                    )
            _validate_offsets(grid, values)
    except Exception:
        _restore_lines(grid, snapshots)
        raise


def apply_line_contents(grid, rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...]) -> None:
    """Patch source-revision-bound Bytes, Raw, and Decoded Text rows."""

    editors = _configured_content_editors(grid)
    snapshots = _line_snapshots(editors, tuple(index for index, _ in rows))
    try:
        with projection_transaction(grid, history_editors=editors):
            _apply_content_rows(grid, rows)
            _validate_contents(grid, rows)
    except Exception:
        _restore_lines(grid, snapshots)
        raise


def apply_bytes_line_contents(
    grid,
    rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
) -> None:
    """Project Bytes-origin content peers without rewriting the active editor."""

    editors = (
        grid.instructions,
        *tuple(
            editor
            for name, editor in (
                (BINARY_WORKBENCH_TEXT.DECODED_TEXT, grid.decoded_text),
                (BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, grid.raw_instructions),
            )
            if _column_is_configured(grid, name)
        ),
    )
    snapshots = _line_snapshots(editors, tuple(index for index, _ in rows))
    try:
        with projection_transaction(
            grid,
            history_exclude=(grid.bytes,),
            history_editors=editors,
        ):
            for index, row in rows:
                _replace_line(
                    grid.instructions,
                    index,
                    grid._display_instruction(row.instruction),
                )
                if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.DECODED_TEXT):
                    _replace_line(
                        grid.decoded_text,
                        index,
                        grid._display_decoded_row(row),
                    )
                if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS):
                    _replace_line(
                        grid.raw_instructions,
                        index,
                        grid._display_raw_row(row),
                    )
            _validate_bytes_line_contents(grid, rows)
    except Exception:
        _restore_lines(grid, snapshots)
        raise


def apply_semantic_projection(
    grid,
    offsets: tuple[tuple[int, dict[str, str]], ...],
    rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
) -> None:
    """Atomically project semantic offsets and source-bound row contents."""

    indices = tuple(sorted({index for index, _ in offsets} | {index for index, _ in rows}))
    editors = _derived_editors(grid)
    snapshots = _line_snapshots(editors, indices)
    try:
        with projection_transaction(grid, history_editors=editors):
            for index, values in offsets:
                for name, editor in grid._offset_editors.items():
                    _replace_line(
                        editor,
                        index,
                        grid._display_offset_row(
                            index,
                            name,
                            values.get(name, "-"),
                        ),
                    )
            _apply_content_rows(grid, rows)
            _validate_offsets(grid, offsets)
            _validate_contents(grid, rows)
    except Exception:
        _restore_lines(grid, snapshots)
        raise


def apply_full_projection(grid, rows: list[BinaryWorkbenchRowDTO]) -> None:
    """Replace every derived document transactionally for a barrier commit."""

    removed = max((editor.document().blockCount() for editor in _derived_editors(grid)), default=1)
    apply_structure_splice(grid, 0, removed, rows)


def _apply_content_rows(
    grid,
    rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
) -> None:
    for index, row in rows:
        if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.BYTES):
            _replace_line(grid.bytes, index, grid._display_bytes_row(row))
        if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.DECODED_TEXT):
            _replace_line(
                grid.decoded_text,
                index,
                grid._display_decoded_row(row),
            )
        if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS):
            _replace_line(
                grid.raw_instructions,
                index,
                grid._display_raw_row(row),
            )


def _replace_line(editor, index: int, text: str) -> None:
    block = editor.document().findBlockByNumber(index)
    if not block.isValid() or block.text() == text:
        return
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    cursor.insertText(text)
    refresh = getattr(editor, "refresh_offset_block", None)
    if refresh is not None:
        refresh(index)


def _replace_span(editor, first: int, removed: int, lines: list[str]) -> None:
    document = editor.document()
    count = document.blockCount()
    first = min(max(0, first), count)
    cursor = QTextCursor(document)
    if removed == 0:
        if first >= count:
            cursor.movePosition(QTextCursor.End)
            prefix = "\n" if document.characterCount() > 1 else ""
            cursor.insertText(prefix + "\n".join(lines))
            return
        set_cursor_position(cursor, document.findBlockByNumber(first).position())
        cursor.insertText("\n".join(lines) + ("\n" if lines else ""))
        return
    start = document.findBlockByNumber(min(first, count - 1)).position()
    after = first + removed
    if after < count:
        end = document.findBlockByNumber(after).position()
        replacement = "\n".join(lines) + ("\n" if lines else "")
    else:
        end = document.characterCount() - 1
        if first > 0:
            start -= 1
            replacement = ("\n" + "\n".join(lines)) if lines else ""
        else:
            replacement = "\n".join(lines)
    set_cursor_position(cursor, start)
    set_cursor_position(cursor, end, QTextCursor.KeepAnchor)
    cursor.insertText(replacement)


def _refresh_fold_visibility(grid, *, render_offsets: bool = True) -> None:
    previous = grid._label_fold_regions
    regions = label_fold_regions(grid._rows) if grid._label_folding_enabled else []
    grid._label_fold_regions = regions
    grid._label_fold_regions_by_row = {
        region.label_row: region for region in regions
    }
    grid._directive_fold_region = (
        debugger_directive_fold_region(grid._rows)
        if grid._label_folding_enabled
        else None
    )
    if grid._directive_fold_region is None:
        grid._directives_collapsed = False
    grid._expand_owners_of_removed_labels(previous, regions)
    grid._collapsed_labels.intersection_update({item.label for item in regions})
    hidden = grid._folded_hidden_rows()
    grid.instructions.set_label_fold_regions(
        {item.label_row: (item.label, item.label in grid._collapsed_labels) for item in regions}
    )
    directive = grid._directive_fold_region
    grid.instructions.set_directive_fold_region(
        (directive.header_row, grid._directives_collapsed)
        if directive is not None
        else None
    )
    if render_offsets:
        grid._render_offsets()
    for editor in grid._fold_editors():
        grid._apply_hidden_rows(editor, hidden)


def _rebuild_bytes_origin_projection(grid) -> None:
    """Repair every Bytes-origin peer from the committed row model."""

    rows = list(grid._rows)
    with projection_transaction(
        grid,
        refresh_structure=True,
        refresh_fold_offsets=False,
    ):
        for name, editor in grid._offset_editors.items():
            _replace_document(
                editor,
                [
                    grid._display_offset_row(index, name, row.offsets.get(name, "-"))
                    for index, row in enumerate(rows)
                ],
            )
        if (
            _column_is_configured(grid, BINARY_WORKBENCH_TEXT.BYTES)
            and grid.bytes.document().blockCount() != max(1, len(rows))
        ):
            _replace_document(
                grid.bytes,
                [grid._display_bytes_row(row) for row in rows],
            )
        if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.DECODED_TEXT):
            _replace_document(
                grid.decoded_text,
                [grid._display_decoded_row(row) for row in rows],
            )
        if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS):
            _replace_document(
                grid.raw_instructions,
                [grid._display_raw_row(row) for row in rows],
            )
        _replace_document(
            grid.instructions,
            [grid._display_instruction(row.instruction) for row in rows],
        )
        _refresh_offset_overlays(grid)
        _validate_block_counts(grid)


def _refresh_offset_overlays(grid) -> None:
    for editor in _derived_editors(grid):
        rebuild = getattr(editor, "_rebuild_dash_labels", None)
        if rebuild is not None:
            rebuild()


def _derived_editors(grid) -> tuple:
    """Return only materialized columns; hidden columns must not add Qt work."""

    return (*grid._offset_editors.values(), *_configured_content_editors(grid))


def _configured_content_editors(grid) -> tuple:
    """Exclude hidden legacy projections from large structural commits."""

    return tuple(
        editor
        for name, editor in (
            (BINARY_WORKBENCH_TEXT.BYTES, grid.bytes),
            (BINARY_WORKBENCH_TEXT.DECODED_TEXT, grid.decoded_text),
            (BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, grid.raw_instructions),
        )
        if _column_is_configured(grid, name)
    )


def _column_is_configured(grid, name: str) -> bool:
    """Report whether a derived column is part of the current user layout."""

    return name in getattr(grid, "_configured_columns", ())


def _document_snapshots(editors: tuple) -> tuple[tuple[object, str], ...]:
    return tuple((editor, editor.toPlainText()) for editor in editors)


def _line_snapshots(editors: tuple, indices: tuple[int, ...]) -> tuple:
    snapshots = []
    for editor in editors:
        values = []
        for index in indices:
            block = editor.document().findBlockByNumber(index)
            if block.isValid():
                values.append((index, block.text()))
        snapshots.append((editor, tuple(values)))
    return tuple(snapshots)


def _restore_documents(grid, snapshots: tuple, *, refresh_structure: bool) -> None:
    with projection_transaction(grid, refresh_structure=refresh_structure):
        for editor, text in snapshots:
            cursor = QTextCursor(editor.document())
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(text)
        _refresh_offset_overlays(grid)


def _rebuild_derived_documents(grid) -> None:
    """Reconcile every projection with the current authoritative row model."""

    rows = list(grid._rows)
    with projection_transaction(grid, refresh_structure=True):
        for name, editor in grid._offset_editors.items():
            _replace_document(
                editor,
                [
                    grid._display_offset_row(index, name, row.offsets.get(name, "-"))
                    for index, row in enumerate(rows)
                ],
            )
        if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.BYTES):
            _replace_document(
                grid.bytes,
                [grid._display_bytes_row(row) for row in rows],
            )
        if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.DECODED_TEXT):
            _replace_document(
                grid.decoded_text,
                [grid._display_decoded_row(row) for row in rows],
            )
        if _column_is_configured(grid, BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS):
            _replace_document(
                grid.raw_instructions,
                [grid._display_raw_row(row) for row in rows],
            )
        _refresh_offset_overlays(grid)
        _validate_block_counts(grid)


def _replace_document(editor, lines: list[str]) -> None:
    cursor = QTextCursor(editor.document())
    cursor.select(QTextCursor.SelectionType.Document)
    cursor.insertText("\n".join(lines))


def _snapshots_match_source(grid, snapshots: tuple) -> bool:
    expected = grid.instructions.document().blockCount()
    return all(text.count("\n") + 1 == expected for _editor, text in snapshots)


def _restore_lines(grid, snapshots: tuple) -> None:
    with projection_transaction(grid):
        for editor, values in snapshots:
            for index, text in values:
                _replace_line(editor, index, text)


def _validate_block_counts(grid) -> None:
    expected = grid.instructions.document().blockCount()
    if any(editor.document().blockCount() != expected for editor in _derived_editors(grid)):
        raise RuntimeError("Derived editor block counts diverged from the Assembly source.")


def _validate_offsets(grid, values: tuple[tuple[int, dict[str, str]], ...]) -> None:
    _validate_block_counts(grid)
    for index, offsets in values:
        for name, editor in grid._offset_editors.items():
            block = editor.document().findBlockByNumber(index)
            expected = grid._display_offset_row(
                index,
                name,
                offsets.get(name, "-"),
            )
            if not block.isValid() or block.text() != expected:
                raise RuntimeError(f"Offset projection failed at line {index + 1}.")


def _validate_contents(grid, rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...]) -> None:
    _validate_block_counts(grid)
    for index, row in rows:
        expected = tuple(
            (editor, text)
            for name, editor, text in (
                (BINARY_WORKBENCH_TEXT.BYTES, grid.bytes, grid._display_bytes_row(row)),
                (BINARY_WORKBENCH_TEXT.DECODED_TEXT, grid.decoded_text, grid._display_decoded_row(row)),
                (BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, grid.raw_instructions, grid._display_raw_row(row)),
            )
            if _column_is_configured(grid, name)
        )
        if any(
            not editor.document().findBlockByNumber(index).isValid()
            or editor.document().findBlockByNumber(index).text() != text
            for editor, text in expected
        ):
            raise RuntimeError(f"Content projection failed at line {index + 1}.")


def _validate_bytes_line_contents(
    grid,
    rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...],
) -> None:
    _validate_block_counts(grid)
    for index, row in rows:
        expected = (
            (grid.instructions, grid._display_instruction(row.instruction)),
            *tuple(
                (editor, text)
                for name, editor, text in (
                    (BINARY_WORKBENCH_TEXT.DECODED_TEXT, grid.decoded_text, grid._display_decoded_row(row)),
                    (BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, grid.raw_instructions, grid._display_raw_row(row)),
                )
                if _column_is_configured(grid, name)
            ),
        )
        if any(
            not editor.document().findBlockByNumber(index).isValid()
            or editor.document().findBlockByNumber(index).text() != text
            for editor, text in expected
        ):
            raise RuntimeError(f"Bytes peer projection failed at line {index + 1}.")


def _row_address(row: BinaryWorkbenchRowDTO) -> int:
    try:
        return int(row.offsets.get("File", "0"), 0)
    except ValueError:
        return 0
