from __future__ import annotations

from src.core.binary_workbench.version_line_comments import apply_line_comments
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    update_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.editor.page_overlays import (
    instruction_overlays_with_changed_rows,
)


def active_version_rows(
    context: BinaryWorkbenchTabContextDTO,
    rows: list,
) -> list:
    version = next(
        (item for item in context.versions if item.name == context.active_version_name),
        None,
    )
    if version is None or not version.instructions_by_line:
        return rows
    return apply_line_comments(rows, version.instructions_by_line, context.reference_offsets)


def instruction_overlays_for_rows(context, grid, rows: list) -> dict[str, str]:
    origin = grid.edit_origin_kind()
    if origin == BINARY_WORKBENCH_TEXT.INSTRUCTION:
        return update_instruction_overlays(context.instruction_overlays, rows, context.rows)
    if origin == BINARY_WORKBENCH_TEXT.BYTES:
        return instruction_overlays_with_changed_rows(
            context.instruction_overlays,
            rows,
            context.rows,
        )
    if grid.focused_editor_kind() != BINARY_WORKBENCH_TEXT.INSTRUCTION:
        return dict(context.instruction_overlays)
    return update_instruction_overlays(context.instruction_overlays, rows, context.rows)
