from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QTextEdit

from src.core.binary_workbench.mips_r3000a import (
    raw_mips_instruction,
    validate_mips_hazards,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.constants.raw_instruction_style import (
    RAW_INSTRUCTION_HAZARD_ERROR_BACKGROUND_RGBA,
    RAW_INSTRUCTION_HAZARD_WARNING_BACKGROUND_RGBA,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import address_from_row


class GridRawInstructionsMixin:
    def _render_raw_instructions(self) -> None:
        lines = self._raw_instruction_lines()
        self._set_editor_text(self.raw_instructions, lines)
        self._raw_instruction_highlighter.rehighlight()
        self._apply_raw_hazards(validate_mips_hazards(lines))

    def _raw_instruction_lines(self) -> list[str]:
        lines: list[str] = []
        for row in self._rows:
            address = address_from_row(row)
            lines.append(
                self._raw_instruction_from_bytes(row.bytes_text, address)
                or raw_mips_instruction(
                    row.instruction,
                    address,
                    self._labels,
                    self._variables,
                    self._equates,
                )
            )
        return lines

    def _raw_instruction_from_bytes(self, bytes_text: str, address: int) -> str:
        try:
            data = bytes.fromhex(bytes_text.replace(" ", ""))
        except ValueError:
            return ""
        if not data:
            return ""
        return self._codec.disassemble(data[:ROW_BYTES].ljust(ROW_BYTES, b"\x00"), address)

    def _apply_raw_hazards(self, hazards) -> None:
        document = self.raw_instructions.document()
        self.raw_instructions.setExtraSelections(
            [
                self._raw_hazard_selection(
                    document.findBlockByNumber(item.line_index),
                    item.severity,
                )
                for item in hazards
            ]
        )

    def _raw_hazard_selection(self, block, severity: str) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        selection.cursor = self.raw_instructions.textCursor()
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
