from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchTabContextDTO,
)
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
        updated = BinaryWorkbenchTabContextDTO(
            **{
                **current.__dict__,
                "variables": variables,
                "equates": equates,
                "labels": labels,
                "rows": rows,
                "symbol_offsets": symbol_offsets(rows, variables, equates, labels),
            }
        )
        self._set_current_context(updated)

    def save_current_symbols(self, name: str) -> None:
        return

    def load_current_symbols(self, name: str) -> bool:
        return False
