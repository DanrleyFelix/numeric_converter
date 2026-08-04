from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from src.modules.utils import read_json, write_json
from src.presentation.repository.binary_workbench_workspace.payloads import (
    offset_region_details_from_payload,
    offset_regions_from_payload,
    offset_regions_payload_preserving_details,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import BINARY_WORKBENCH_FILE_DIALOG_TEXT


class OffsetRegionsFileActionsMixin:
    """Keep offset-region persistence behind the established native dialogs."""

    def _load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, BINARY_WORKBENCH_TEXT.OFFSET_REGIONS, self._directory,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.OFFSET_REGIONS_JSON_FILTER,
        )
        payload = read_json(Path(path)) if path else None
        if not isinstance(payload, dict) or not isinstance(payload.get("regions"), list):
            return
        self._replace_regions(offset_regions_from_payload(payload, include_details=False))
        self._loaded_path = path
        self._details_source_path = Path(path)
        self._details_loader = lambda name, offset, source=Path(path): offset_region_details_from_payload(
            read_json(source), name, offset
        )
        self._remember_directory(Path(path))

    def _save(self) -> None:
        initial = str(Path(self._directory) / BINARY_WORKBENCH_FILE_DIALOG_TEXT.OFFSET_REGIONS_DEFAULT_FILENAME)
        path, _ = QFileDialog.getSaveFileName(
            self, BINARY_WORKBENCH_TEXT.OFFSET_REGIONS, initial,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.OFFSET_REGIONS_JSON_FILTER,
        )
        if not path:
            return
        target = Path(path) if Path(path).suffix.lower() == ".json" else Path(path).with_suffix(".json")
        source = self._details_source_path or target
        payload = offset_regions_payload_preserving_details(target.stem, self.mappings(), read_json(source))
        write_json(target, payload)
        self._saved_path = str(target)
        self._remember_directory(target)

    def _remember_directory(self, path: Path) -> None:
        self._directory = str(path.parent)
        self.directoryChanged.emit(self._directory)
