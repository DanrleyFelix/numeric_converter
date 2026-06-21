from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES


class GridOffsetsMixin:
    def _row_at(self, index: int) -> BinaryWorkbenchRowDTO:
        if index < len(self._rows):
            return self._rows[index]
        return BinaryWorkbenchRowDTO(offsets=self._offsets_for_row(index))

    def _offsets_for_row(self, index: int) -> dict[str, str]:
        start_offset = self._visible_start_offset if self._virtual else 0
        file_offset = start_offset + (index * ROW_BYTES)
        bases = self._offset_bases()
        names = self._columns or [BINARY_WORKBENCH_TEXT.FILE]
        return {name: f"0x{bases.get(name, 0) + file_offset:08X}" for name in names}

    def _offset_bases(self) -> dict[str, int]:
        if not self._rows:
            return {BINARY_WORKBENCH_TEXT.FILE: 0}
        first = next(
            (
                row
                for row in self._rows
                if row.offsets.get(BINARY_WORKBENCH_TEXT.FILE, "-") != "-"
            ),
            None,
        )
        if first is None:
            return {BINARY_WORKBENCH_TEXT.FILE: 0}
        file_offset = offset_int(first.offsets.get(BINARY_WORKBENCH_TEXT.FILE) or first.offsets.get(BINARY_WORKBENCH_TEXT.FILE_OFFSET))
        return {
            name: offset_int(value) - file_offset
            for name, value in first.offsets.items()
        }

    def _aligned_scroll_offset(self, value: int) -> int:
        return max(0, value - (value % ROW_BYTES))


def offset_int(value: str | None) -> int:
    try:
        return int(value or "0x0", 16)
    except ValueError:
        return 0
