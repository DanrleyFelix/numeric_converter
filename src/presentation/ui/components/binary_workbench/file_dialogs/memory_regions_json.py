from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from src.modules.utils import read_json, write_json
from src.presentation.repository.binary_workbench_workspace.payloads import (
    memory_regions_from_payload,
    memory_regions_payload,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class MemoryRegionsJsonMixin:
    def load_json(self, path: Path) -> bool:
        regions = memory_regions_from_payload(read_json(path))
        self._clear_rows()
        for region in regions:
            self._append_row(region.name, str(region.start_offset), str(region.end_offset))
        self._json_path = str(path)
        self._remember_directory(path)
        return bool(regions)

    def save_json(self, path: Path) -> bool:
        target = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
        write_json(target, memory_regions_payload(target.stem, self.regions()))
        self._json_path = str(target)
        self._remember_directory(target)
        self.status.setText(
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_SAVED_TEMPLATE.format(
                path=str(target)
            )
        )
        return True

    def _load_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_TITLE,
            self._directory,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_JSON_FILTER,
        )
        if path and self.load_json(Path(path)):
            self.status.setText(
                BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_LOADED_TEMPLATE.format(
                    path=path
                )
            )

    def _save_dialog(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_TITLE,
            self._directory,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.MEMORY_REGIONS_JSON_FILTER,
        )
        if path:
            self.save_json(Path(path))

    def _remember_directory(self, path: Path) -> None:
        self._directory = str(path.parent)
        self.directoryChanged.emit(self._directory)
