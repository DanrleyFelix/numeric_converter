from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QTextEdit

from src.core.binary_workbench.mips_r3000a import (
    raw_mips_instruction,
    validate_mips_hazards,
)
from src.presentation.ui.components.binary_workbench.editor.constants.raw_instruction_style import (
    RAW_INSTRUCTION_HAZARD_BACKGROUND_RGBA,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import address_from_row


class GridRawInstructionsMixin:
    def _render_raw_instructions(self) -> None:
        lines = self._raw_instruction_lines()
        self._set_editor_text(self.raw_instructions, lines)
        self._apply_raw_hazards(validate_mips_hazards(lines))

    def _raw_instruction_lines(self) -> list[str]:
        return [
            raw_mips_instruction(
                row.instruction,
                address_from_row(row),
                self._labels,
                self._variables,
                self._equates,
            )
            for row in self._rows
        ]

    def _apply_raw_hazards(self, hazards) -> None:
        document = self.raw_instructions.document()
        self.raw_instructions.setExtraSelections(
            [self._raw_hazard_selection(document.findBlockByNumber(item.line_index)) for item in hazards]
        )

    def _raw_hazard_selection(self, block) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        selection.cursor = self.raw_instructions.textCursor()
        selection.cursor.setPosition(block.position())
        selection.cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        selection.format = QTextCharFormat()
        selection.format.setBackground(QColor(*RAW_INSTRUCTION_HAZARD_BACKGROUND_RGBA))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        return selection
