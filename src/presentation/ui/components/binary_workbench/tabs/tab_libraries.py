from src.core.binary_workbench.resource_identity import merged_file_identifiers
from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchLbaFilesystemDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchSymbolsDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import (
    current_identifiers,
    lba_sector_size,
    state_payload,
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
        current = self.current_context()
        name = name.strip()
        if current is None or not name:
            return
        identifiers = current_identifiers(current)
        existing = next((item for item in self._state.lba_filesystems if item.name == name), None)
        saved = BinaryWorkbenchLbaFilesystemDTO(
            name=name,
            file_identifiers=merged_file_identifiers(existing.file_identifiers if existing else [], identifiers),
            sector_size=current.lba_sector_size,
            internal_files=list(current.internal_files),
        )
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "lba_filesystems": [*[item for item in self._state.lba_filesystems if item.name != saved.name], saved]}
        )
        self.stateChanged.emit(self._state)

    def load_current_lba_filesystem(self, name: str) -> bool:
        filesystem = next((item for item in self._state.lba_filesystems if item.name == name), None)
        if filesystem is None:
            return False
        self.set_current_internal_files(list(filesystem.internal_files), filesystem.sector_size)
        return True

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
        current = self.current_context()
        name = name.strip()
        if current is None or not name:
            return
        identifiers = current_identifiers(current)
        existing = next((item for item in self._state.symbols if item.name == name), None)
        saved = BinaryWorkbenchSymbolsDTO(
            name=name,
            file_identifiers=merged_file_identifiers(existing.file_identifiers if existing else [], identifiers),
            variables=dict(current.variables),
            equates=dict(current.equates),
            labels={},
        )
        self._state = BinaryWorkbenchStateDTO(
            **{**state_payload(self._state), "symbols": [*[item for item in self._state.symbols if item.name != saved.name], saved]}
        )
        self.stateChanged.emit(self._state)

    def load_current_symbols(self, name: str) -> bool:
        symbols = next((item for item in self._state.symbols if item.name == name), None)
        if symbols is None:
            return False
        self.set_current_symbols(dict(symbols.variables), dict(symbols.equates), {})
        return True
