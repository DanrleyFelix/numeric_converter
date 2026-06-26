from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from src.modules.binary_workbench_dtos import BinaryWorkbenchSymbolsDTO
from src.modules.utils import read_json, write_json
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class SymbolsDialogJsonMixin:
    def load_library_json(self, path: Path) -> bool:
        library = symbols_from_json_payload(read_json(path), path.stem)
        if library is None:
            return False
        self._clear_rows()
        self._loaded_library_name = library.name
        self._loaded_library_path = str(path)
        self._load_rows(library.variables, library.equates, library.labels)
        self._remember_symbols_directory(path)
        return True

    def save_library_json(self, path: Path) -> bool:
        target = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
        library_name = target.stem
        variables, equates, _ = self.values()
        write_json(target, symbols_payload(library_name, variables, equates))
        self._save_requested = True
        self._saved_library_name = library_name
        self._saved_library_path = str(target)
        self._remember_symbols_directory(target)
        return True

    def _load_library_json_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            BINARY_WORKBENCH_TEXT.SYMBOLS_TITLE,
            self._symbols_directory,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.SYMBOLS_JSON_FILTER,
        )
        if path:
            self.load_library_json(Path(path))

    def _save_library_json_dialog(self) -> None:
        initial = str(Path(self._symbols_directory) / symbols_filename(self.saved_library_name() or self.loaded_library_name()))
        path, _ = QFileDialog.getSaveFileName(
            self,
            BINARY_WORKBENCH_TEXT.SYMBOLS_TITLE,
            initial,
            BINARY_WORKBENCH_FILE_DIALOG_TEXT.SYMBOLS_JSON_FILTER,
        )
        if path:
            self.save_library_json(Path(path))

    def _remember_symbols_directory(self, path: Path) -> None:
        self._symbols_directory = str(path.parent)
        self.directoryChanged.emit(self._symbols_directory)


def symbols_from_json_payload(payload: dict[str, object] | None, fallback_name: str) -> BinaryWorkbenchSymbolsDTO | None:
    if payload is None:
        return None
    raw = payload.get("binary_workbench", payload)
    if isinstance(raw, dict) and isinstance(raw.get("symbols"), list):
        raw = raw["symbols"][0] if raw["symbols"] else {}
    if not isinstance(raw, dict):
        return None
    return BinaryWorkbenchSymbolsDTO(
        name=_text_value(raw.get("name")) or fallback_name,
        variables=_string_map(raw.get("variables")),
        equates=_string_map(raw.get("equates")),
        labels={},
    )


def symbols_payload(name: str, variables: dict[str, str], equates: dict[str, str]) -> dict[str, object]:
    return {"name": name, "variables": variables, "equates": equates}


def symbols_filename(name: str) -> str:
    return f"{name.strip() or BINARY_WORKBENCH_TEXT.SYMBOLS_TITLE}.json"


def _string_map(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _text_value(raw: object) -> str:
    return raw if isinstance(raw, str) else ""
