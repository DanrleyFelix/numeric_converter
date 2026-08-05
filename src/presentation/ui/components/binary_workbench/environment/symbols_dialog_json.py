from pathlib import Path
from shutil import copy2
from uuid import NAMESPACE_URL, uuid5

from PySide6.QtWidgets import QFileDialog

from src.modules.binary_workbench_dtos import BinaryWorkbenchSymbolsDTO
from src.core.binary_workbench.symbol_values import merged_symbol_values
from src.core.binary_workbench.symbols.compatibility import (
    LegacySymbolsPayloadAdapter,
    SYMBOL_SCHEMA_VERSION,
    definitions_payload,
)
from src.core.binary_workbench.symbols.definitions import SymbolScope
from src.modules.utils import read_json, write_json
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class SymbolsDialogJsonMixin:
    def load_library_json(self, path: Path) -> bool:
        payload = read_json(path)
        library = symbols_from_json_payload(payload, path.stem)
        if library is None:
            return False
        if _direct_legacy_library(payload):
            _migrate_library_file(path, library.name, library.symbols)
        self._loaded_library_name = library.name
        self._loaded_library_path = str(path)
        self._merge_rows(library.symbols)
        self._remember_symbols_directory(path)
        return True

    def save_library_json(self, path: Path) -> bool:
        target = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
        library_name = target.stem
        symbols, _, _ = self.values()
        write_json(target, symbols_payload(library_name, symbols))
        self.symbolsChanged.emit(symbols)
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
    module_name = _text_value(raw.get("name")) or fallback_name
    module_id = str(raw.get("module_id") or uuid5(
        NAMESPACE_URL,
        f"binary-workbench-symbol-module:{module_name.casefold()}",
    ))
    adapted = LegacySymbolsPayloadAdapter(module_id).adapt(
        raw,
        SymbolScope.LOCAL,
        f"module:{module_id}",
    )
    return BinaryWorkbenchSymbolsDTO(
        name=module_name,
        symbols={item.name: item.value for item in adapted.definitions},
        labels={},
    )


def symbols_payload(name: str, symbols: dict[str, str]) -> dict[str, object]:
    values = merged_symbol_values(symbols)
    module_id = str(uuid5(NAMESPACE_URL, f"binary-workbench-symbol-module:{name.casefold()}"))
    definitions = tuple(LegacySymbolsPayloadAdapter(module_id).from_mapping(
        values,
        SymbolScope.LOCAL,
        f"module:{module_id}",
    ))
    return {
        "schema_version": SYMBOL_SCHEMA_VERSION,
        "module_id": module_id,
        "name": name,
        "symbol_definitions": definitions_payload(definitions),
        "symbols": values,
    }


def symbols_filename(name: str) -> str:
    return f"{name.strip() or BINARY_WORKBENCH_TEXT.SYMBOLS_TITLE}.json"


def _direct_legacy_library(payload: object) -> bool:
    return (
        isinstance(payload, dict)
        and "binary_workbench" not in payload
        and "symbol_definitions" not in payload
        and any(key in payload for key in ("symbols", "variables", "equates"))
    )


def _migrate_library_file(path: Path, name: str, symbols: dict[str, str]) -> bool:
    """Back up and atomically migrate a direct external Symbols library."""

    migrated = symbols_payload(name, symbols)
    temporary = path.with_name(f".{path.name}.symbols-v3.tmp")
    try:
        write_json(temporary, migrated)
        if read_json(temporary) != migrated:
            return False
        copy2(path, path.with_suffix(path.suffix + ".v2.bak"))
        temporary.replace(path)
        return True
    except OSError:
        return False
    finally:
        temporary.unlink(missing_ok=True)


def _text_value(raw: object) -> str:
    return raw if isinstance(raw, str) else ""
