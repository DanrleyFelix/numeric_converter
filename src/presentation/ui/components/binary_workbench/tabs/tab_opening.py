from pathlib import Path

from src.core.binary_workbench.file_ops import extract_internal_file_bytes
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.tabs.factory import (
    create_assembly_tab,
    create_binary_tab,
    create_file_tab,
    create_internal_tab,
    create_scratch_tab,
)


class TabOpeningMixin:
    def open_binary_path(self, path: Path) -> None:
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_BINARY_DIRECTORY, path)
        self._append_tab(create_binary_tab(self._state, path))

    def open_file_path(self, path: Path) -> None:
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_FILE_DIRECTORY, path)
        self._append_tab(create_file_tab(self._state, path))

    def open_assembly_path(self, path: Path) -> None:
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_ASSEMBLY_DIRECTORY, path)
        self._append_tab(create_assembly_tab(self._state, path))

    def new_scratch_tab(self) -> None:
        self._append_tab(create_scratch_tab(self._state))

    def open_internal_tab(self, internal_name: str) -> None:
        current = self.current_context()
        if current is None or not current.source_path or not current.internal_files:
            self.statusChanged.emit(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_SOURCE_REQUIRED)
            return
        source = Path(current.source_path)
        target = next((item for item in current.internal_files if item.name == internal_name), None)
        if target is None:
            return
        data = extract_internal_file_bytes(source, target, current.internal_files, current.lba_sector_size)
        self._append_tab(create_internal_tab(self._state, current, target, data))
