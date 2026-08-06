from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QTextEdit

from src.core.binary_workbench.mips_r3000a import validate_mips_hazards
from src.core.binary_workbench.mips_r3000a.hazard_validator import MipsHazard
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.constants.raw_instruction_style import (
    RAW_INSTRUCTION_HAZARD_ERROR_BACKGROUND_RGBA,
    RAW_INSTRUCTION_HAZARD_WARNING_BACKGROUND_RGBA,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import address_from_row


class GridRawInstructionsMixin:
    """Project costly Raw text near the viewport to avoid large-file stalls."""

    def _render_raw_instructions(self) -> None:
        """Materialize Raw Instructions only near the initial viewport."""

        lines = self._raw_instruction_lines()
        self._set_editor_text(self.raw_instructions, lines)
        self.raw_instructions.set_hazard_extra_selections([])
        first, last = self._highlighter_projection_range()
        self._refresh_visible_instruction_hazards(first, last)
        hidden_rows = self._folded_hidden_rows() if self._label_folding_enabled else set()
        if hidden_rows:
            self._apply_hidden_rows(self.raw_instructions, hidden_rows)

    def _raw_instruction_lines(self) -> list[str]:
        if len(self._rows) <= BINARY_WORKBENCH_LAYOUT.EDITOR_LAZY_RAW_THRESHOLD:
            self._raw_projected_rows = set(range(len(self._rows)))
            return [self._display_raw_row(row) for row in self._rows]
        first, last = self._highlighter_projection_range()
        self._raw_projected_rows = set(range(first, min(last + 1, len(self._rows))))
        return [
            self._display_raw_row(row) if index in self._raw_projected_rows else ""
            for index, row in enumerate(self._rows)
        ]

    def _materialize_raw_projection(self, first: int, last: int) -> None:
        """Fill newly visible Raw rows without scanning the complete document."""

        pending = [
            index
            for index in range(max(0, first), min(len(self._rows), last + 1))
            if index not in getattr(self, "_raw_projected_rows", set())
        ]
        self._set_editor_lines(
            self.raw_instructions,
            {
                index: self._display_raw_row(self._rows[index])
                for index in pending
            },
        )
        self._raw_projected_rows.update(pending)

    def _refresh_raw_projection(self, first: int, last: int) -> None:
        """Refresh a bounded Raw window after a Symbol catalog revision."""

        indices = range(max(0, first), min(len(self._rows), last + 1))
        self._set_editor_lines(
            self.raw_instructions,
            {
                index: self._display_raw_row(self._rows[index])
                for index in indices
            },
        )
        projected = getattr(self, "_raw_projected_rows", set())
        projected.update(indices)
        self._raw_projected_rows = projected
        self.raw_instructions.set_hazard_extra_selections([])
        self._refresh_visible_instruction_hazards(first, last)

    def _raw_instruction_from_bytes(self, bytes_text: str, address: int) -> str:
        try:
            data = bytes.fromhex(bytes_text.replace(" ", ""))
        except ValueError:
            return ""
        if not data:
            return ""
        return self._codec.disassemble(data[:ROW_BYTES].ljust(ROW_BYTES, b"\x00"), address)

    def _apply_instruction_hazards(self, hazards) -> None:
        document = self.instructions.document()
        self.instructions.set_hazard_extra_selections(
            [
                self._instruction_hazard_selection(
                    document.findBlockByNumber(item.line_index),
                    item.severity,
                )
                for item in hazards
            ]
        )

    def _refresh_visible_instruction_hazards(self, first: int, last: int) -> None:
        """Validate only the active viewport and its bounded prefetch window."""

        start = max(0, first - 1)
        stop = min(len(self._rows), last + 1)
        hazards = validate_mips_hazards(
            [row.instruction for row in self._rows[start:stop]]
        )
        self._apply_instruction_hazards(
            [MipsHazard(item.line_index + start, item.severity, item.message) for item in hazards]
        )

    def _instruction_hazard_selection(self, block, severity: str) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        selection.cursor = self.instructions.textCursor()
        set_cursor_position(selection.cursor, block.position())
        selection.cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        selection.format = QTextCharFormat()
        rgba = (
            RAW_INSTRUCTION_HAZARD_ERROR_BACKGROUND_RGBA
            if severity == "error"
            else RAW_INSTRUCTION_HAZARD_WARNING_BACKGROUND_RGBA
        )
        selection.format.setBackground(QColor(*rgba))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        return selection
