from src.core.binary_workbench.byte_replacement import (
    bytes_from_rows,
)
from src.core.binary_workbench.byte_replacement_growth import (
    replaced_or_extended_row_byte_lines,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT


class GridByteReplacementMixin:
    def replacement_bytes_at(self, start: int, size: int) -> bytes | None:
        """Read replacement confirmation bytes from the complete in-memory grid."""

        current_size = self.current_file_size()
        if start < 0 or size < 0 or start > current_size:
            return None
        covered_size = min(size, current_size - start)
        existing = bytes_from_rows(self.export_rows(), start, covered_size)
        if existing is None:
            return None
        extension_size = size - covered_size
        if extension_size and not self.byte_shift_allowed():
            return None
        return existing + bytes(extension_size)

    def replace_bytes_at(self, start: int, data: bytes) -> bool:
        """Replace bytes in non-virtual rows through the normal byte-edit pipeline."""

        lines = replaced_or_extended_row_byte_lines(
            self.export_rows(),
            start,
            data,
            self.byte_shift_allowed(),
        )
        if lines is None:
            return False
        self._sync_user_rows(lines, BINARY_WORKBENCH_TEXT.BYTES)
        return True

    def byte_shift_allowed(self) -> bool:
        """Return whether Rules permits structural byte growth."""

        return self._edit_rules.allow_byte_shift
