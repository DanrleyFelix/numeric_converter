from __future__ import annotations

from contextlib import contextmanager

from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QTextCursor

from src.core.binary_workbench.encoding_tables import decode_hex_bytes
from src.core.binary_workbench.label_folding import label_fold_regions
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


@contextmanager
def projection_transaction(grid, *, refresh_structure: bool = False):
    """Apply one derived projection without exposing intermediate scroll states."""

    editors = [*grid._offset_editors.values(), grid.raw_instructions, grid.bytes, grid.decoded_text]
    scrollbars = [grid.scrollbar, *(editor.verticalScrollBar() for editor in (*editors, grid.instructions))]
    blockers = [QSignalBlocker(item) for item in scrollbars]
    shared_value = grid.scrollbar.value()
    previous_updating = grid._updating
    grid._updating = True
    grid.setUpdatesEnabled(False)
    try:
        yield
        if refresh_structure:
            _refresh_fold_visibility(grid)
            grid._visible_start_offset = shared_value
            grid._configure_scrollbar()
            grid.scrollbar.setValue(min(shared_value, grid.scrollbar.maximum()))
        grid._scroll_static_document(grid.scrollbar.value())
    finally:
        grid._updating = previous_updating
        grid.setUpdatesEnabled(True)
        del blockers
        grid.viewport().update() if hasattr(grid, "viewport") else grid.update()


def apply_structure_splice(
    grid,
    first: int,
    removed: int,
    inserted: list[BinaryWorkbenchRowDTO],
) -> None:
    """Splice every derived document while leaving Assembly text untouched."""

    editors = _derived_editors(grid)
    snapshots = _document_snapshots(editors)
    collapsed = set(grid._collapsed_labels)
    try:
        with projection_transaction(grid, refresh_structure=True):
            for name, editor in grid._offset_editors.items():
                _replace_span(editor, first, removed, [row.offsets.get(name, "-") for row in inserted])
            _replace_span(
                grid.bytes,
                first,
                removed,
                [grid._display_bytes_text(row.bytes_text) for row in inserted],
            )
            _replace_span(
                grid.decoded_text,
                first,
                removed,
                [decode_hex_bytes(row.bytes_text, grid._decoded_text_values) for row in inserted],
            )
            _replace_span(
                grid.raw_instructions,
                first,
                removed,
                [grid._raw_instruction_from_bytes(row.bytes_text, _row_address(row)) for row in inserted],
            )
            _refresh_offset_overlays(grid)
            _validate_block_counts(grid)
    except Exception:
        grid._collapsed_labels = collapsed
        _restore_documents(grid, snapshots, refresh_structure=True)
        raise


def apply_offset_values(grid, values: tuple[tuple[int, dict[str, str]], ...]) -> None:
    """Patch only offset documents for one structural revision batch."""

    editors = tuple(grid._offset_editors.values())
    snapshots = _line_snapshots(editors, tuple(index for index, _ in values))
    try:
        with projection_transaction(grid):
            for index, offsets in values:
                for name, editor in grid._offset_editors.items():
                    _replace_line(
                        editor,
                        index,
                        grid._folded_offset_text(
                            index,
                            name,
                            offsets.get(name, "-"),
                        ),
                    )
            _refresh_offset_overlays(grid)
            _validate_offsets(grid, values)
    except Exception:
        _restore_lines(grid, snapshots)
        raise


def apply_line_contents(grid, rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...]) -> None:
    """Patch source-revision-bound Bytes, Raw, and Decoded Text rows."""

    editors = (grid.bytes, grid.decoded_text, grid.raw_instructions)
    snapshots = _line_snapshots(editors, tuple(index for index, _ in rows))
    try:
        with projection_transaction(grid):
            _apply_content_rows(grid, rows)
            _validate_contents(grid, rows)
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
        with projection_transaction(grid):
            for index, values in offsets:
                for name, editor in grid._offset_editors.items():
                    _replace_line(
                        editor,
                        index,
                        grid._folded_offset_text(
                            index,
                            name,
                            values.get(name, "-"),
                        ),
                    )
            _apply_content_rows(grid, rows)
            _refresh_offset_overlays(grid)
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
        _replace_line(grid.bytes, index, grid._display_bytes_text(row.bytes_text))
        _replace_line(
            grid.decoded_text,
            index,
            decode_hex_bytes(row.bytes_text, grid._decoded_text_values),
        )
        _replace_line(
            grid.raw_instructions,
            index,
            grid._raw_instruction_from_bytes(row.bytes_text, _row_address(row)),
        )


def _replace_line(editor, index: int, text: str) -> None:
    block = editor.document().findBlockByNumber(index)
    if not block.isValid() or block.text() == text:
        return
    cursor = QTextCursor(block)
    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
    cursor.insertText(text)


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
        cursor.setPosition(document.findBlockByNumber(first).position())
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
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    cursor.insertText(replacement)


def _refresh_fold_visibility(grid) -> None:
    previous = grid._label_fold_regions
    regions = label_fold_regions(grid._rows) if grid._label_folding_enabled else []
    grid._label_fold_regions = regions
    grid._expand_owners_of_removed_labels(previous, regions)
    grid._collapsed_labels.intersection_update({item.label for item in regions})
    hidden = grid._folded_hidden_rows()
    grid.instructions.set_label_fold_regions(
        {item.label_row: (item.label, item.label in grid._collapsed_labels) for item in regions}
    )
    grid._render_offsets()
    for editor in grid._fold_editors():
        grid._apply_hidden_rows(editor, hidden)


def _refresh_offset_overlays(grid) -> None:
    for editor in grid._offset_editors.values():
        rebuild = getattr(editor, "_rebuild_dash_labels", None)
        if rebuild is not None:
            rebuild()


def _derived_editors(grid) -> tuple:
    return (*grid._offset_editors.values(), grid.bytes, grid.decoded_text, grid.raw_instructions)


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


def _restore_lines(grid, snapshots: tuple) -> None:
    with projection_transaction(grid):
        for editor, values in snapshots:
            for index, text in values:
                _replace_line(editor, index, text)
        _refresh_offset_overlays(grid)


def _validate_block_counts(grid) -> None:
    expected = grid.instructions.document().blockCount()
    if any(editor.document().blockCount() != expected for editor in _derived_editors(grid)):
        raise RuntimeError("Derived editor block counts diverged from the Assembly source.")


def _validate_offsets(grid, values: tuple[tuple[int, dict[str, str]], ...]) -> None:
    _validate_block_counts(grid)
    for index, offsets in values:
        for name, editor in grid._offset_editors.items():
            block = editor.document().findBlockByNumber(index)
            expected = grid._folded_offset_text(
                index,
                name,
                offsets.get(name, "-"),
            )
            if not block.isValid() or block.text() != expected:
                raise RuntimeError(f"Offset projection failed at line {index + 1}.")


def _validate_contents(grid, rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...]) -> None:
    _validate_block_counts(grid)
    for index, row in rows:
        expected = (
            (grid.bytes, grid._display_bytes_text(row.bytes_text)),
            (grid.decoded_text, decode_hex_bytes(row.bytes_text, grid._decoded_text_values)),
            (grid.raw_instructions, grid._raw_instruction_from_bytes(row.bytes_text, _row_address(row))),
        )
        if any(
            not editor.document().findBlockByNumber(index).isValid()
            or editor.document().findBlockByNumber(index).text() != text
            for editor, text in expected
        ):
            raise RuntimeError(f"Content projection failed at line {index + 1}.")


def _row_address(row: BinaryWorkbenchRowDTO) -> int:
    try:
        return int(row.offsets.get("File", "0"), 0)
    except ValueError:
        return 0
