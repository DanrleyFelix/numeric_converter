from src.core.binary_workbench.byte_editing import byte_row_policy
from src.core.binary_workbench.encoding_tables import decode_hex_bytes
from src.core.binary_workbench.mips_r3000a import raw_mips_instruction
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    address_from_row,
)


class GridDerivedDisplayMixin:
    """Project source-only rows consistently across every derived column."""

    def _row_uses_derived_placeholder(self, row: BinaryWorkbenchRowDTO) -> bool:
        return byte_row_policy(row.instruction, bool(row.bytes_text)).show_placeholder

    def _derived_placeholder(self, row: BinaryWorkbenchRowDTO) -> str | None:
        """Return the neutral marker used by source-only derived rows."""

        policy = byte_row_policy(row.instruction, bool(row.bytes_text))
        return "-" if policy.show_placeholder else None

    def _display_bytes_row(self, row: BinaryWorkbenchRowDTO) -> str:
        if self._row_uses_derived_placeholder(row):
            return ""
        return self._display_bytes_text(row.bytes_text)

    def _display_decoded_row(self, row: BinaryWorkbenchRowDTO) -> str:
        if placeholder := self._derived_placeholder(row):
            return placeholder
        return decode_hex_bytes(row.bytes_text, self._decoded_text_values)

    def _display_raw_row(self, row: BinaryWorkbenchRowDTO) -> str:
        if self._row_uses_derived_placeholder(row):
            return ""
        address = address_from_row(row)
        return self._raw_instruction_from_bytes(row.bytes_text, address) or raw_mips_instruction(
            row.instruction,
            address,
            self._labels,
            self._variables,
            self._equates,
        )

    def _display_offset_row(
        self,
        index: int,
        name: str,
        value: str,
    ) -> str:
        folded = self._folded_offset_text(index, name, value)
        if 0 <= index < len(self._rows):
            placeholder = self._derived_placeholder(self._rows[index])
            if placeholder:
                return folded if folded not in {"", "-"} else placeholder
        return folded
