from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from src.modules.dtos import BinaryWorkbenchInternalFileDTO, BinaryWorkbenchLbaFilesystemDTO
from src.modules.utils import read_json, write_json
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class LbaFilesystemJsonMixin:
    def load_library_json(self, path: Path) -> bool:
        payload = read_json(path)
        library = filesystem_from_json_payload(payload, path.stem)
        if library is None:
            return False
        self._clear_rows()
        self.library_name_input.setText(library.name)
        self._loaded_library_name = library.name
        self._loaded_library_path = str(path)
        self.sector_size.setCurrentText(f"{library.sector_size} bytes")
        for item in library.internal_files:
            self._append_row(item.name, str(item.start_lba))
        self._remember_library_directory(path)
        return True

    def save_library_json(self, path: Path) -> bool:
        target = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
        library_name = self.library_name() or target.stem
        write_json(target, filesystem_payload(library_name, self.selected_lba_sector_size(), self.mappings()))
        self._save_requested = True
        self._saved_library_name = library_name
        self._saved_library_path = str(target)
        self.library_name_input.setText(library_name)
        self._remember_library_directory(target)
        self.status.setText(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_SAVED_TEMPLATE.format(path=str(target)))
        return True

    def _load_library_json_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_TITLE,
            self._library_directory,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_JSON_FILTER,
        )
        if path and self.load_library_json(Path(path)):
            self.status.setText(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_LOADED_TEMPLATE.format(path=path))

    def _save_library_json_dialog(self) -> None:
        initial = str(Path(self._library_directory) / library_filename(self.library_name()))
        path, _ = QFileDialog.getSaveFileName(
            self,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_TITLE,
            initial,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_JSON_FILTER,
        )
        if path:
            self.save_library_json(Path(path))

    def _remember_library_directory(self, path: Path) -> None:
        self._library_directory = str(path.parent)
        self.directoryChanged.emit(self._library_directory)


def filesystem_from_json_payload(
    payload: dict[str, object] | None,
    fallback_name: str,
) -> BinaryWorkbenchLbaFilesystemDTO | None:
    if payload is None:
        return None
    raw = payload.get("binary_workbench", payload)
    if isinstance(raw, dict) and isinstance(raw.get("lba_filesystems"), list):
        raw = raw["lba_filesystems"][0] if raw["lba_filesystems"] else {}
    if not isinstance(raw, dict):
        return None
    files = internal_files_from_payload(raw.get("internal_files"))
    if not files:
        return None
    name = raw.get("name")
    return BinaryWorkbenchLbaFilesystemDTO(
        name=name if isinstance(name, str) and name else fallback_name,
        sector_size=lba_sector_size(raw.get("sector_size")),
        internal_files=files,
    )


def internal_files_from_payload(raw: object) -> list[BinaryWorkbenchInternalFileDTO]:
    if not isinstance(raw, list):
        return []
    files: list[BinaryWorkbenchInternalFileDTO] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("name"), str) and isinstance(item.get("start_lba"), int):
            files.append(BinaryWorkbenchInternalFileDTO(name=item["name"], start_lba=item["start_lba"]))
    return files


def lba_sector_size(raw: object) -> int:
    value = raw if isinstance(raw, int) else 2352
    return value if value in {2048, 2334, 2352} else 2352


def filesystem_payload(
    name: str,
    sector_size: int,
    internal_files: list[BinaryWorkbenchInternalFileDTO],
) -> dict[str, object]:
    return {
        "name": name,
        "sector_size": sector_size,
        "internal_files": [{"name": item.name, "start_lba": item.start_lba} for item in internal_files],
    }


def library_filename(name: str) -> str:
    return f"{name.strip() or BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_TITLE}.json"
