from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TAB_KIND
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import (
    lba_sector_size,
)


class TabLibrariesMixin:
    def set_current_internal_files(
        self,
        internal_files: list[BinaryWorkbenchInternalFileDTO],
        lba_sector_size_value: int | None = None,
    ) -> None:
        current = self.current_context()
        if current is None:
            return
        updates: dict[str, object] = {"internal_files": internal_files}
        if lba_sector_size_value is not None:
            updates["lba_sector_size"] = lba_sector_size(lba_sector_size_value)
        self._set_current_context(BinaryWorkbenchTabContextDTO(**{**current.__dict__, **updates}))

    def save_current_lba_filesystem(self, name: str) -> None:
        return

    def load_current_lba_filesystem(self, name: str) -> bool:
        return False

    def set_current_symbols(self, variables: dict[str, str], equates: dict[str, str], labels: dict[str, str]) -> None:
        current = self.current_context()
        if current is None:
            return
        labels = labels_from_rows(current.rows)
        page = self.currentWidget()
        rows = (
            page.grid.rows_encoded_with_symbols(variables, equates, labels)
            if isinstance(page, BinaryWorkbenchEditorPage)
            else current.rows
        )
        labels = labels_from_rows(rows)
        updates: dict[str, object] = {
            "variables": variables,
            "equates": equates,
            "labels": labels,
            "rows": rows,
            "symbol_offsets": symbol_offsets(rows, variables, equates, labels),
        }
        if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            updates["byte_overlays"] = _byte_overlays_with_symbols(current, variables, equates)
        updated = BinaryWorkbenchTabContextDTO(**{**current.__dict__, **updates})
        self._set_current_context(updated)

    def save_current_symbols(self, name: str) -> None:
        return

    def load_current_symbols(self, name: str) -> bool:
        return False


def _byte_overlays_with_symbols(
    current: BinaryWorkbenchTabContextDTO,
    variables: dict[str, str],
    equates: dict[str, str],
) -> dict[str, str]:
    instruction_offsets = set(current.instruction_overlays)
    byte_overlays = {
        offset: value
        for offset, value in current.byte_overlays.items()
        if offset not in instruction_offsets
    }
    byte_overlays.update(
        byte_overlays_from_instruction_overlays(
            current.instruction_overlays,
            variables,
            equates,
        )
    )
    return byte_overlays
