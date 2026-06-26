from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDialog, QFrame, QLineEdit, QVBoxLayout, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchSymbolsDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_json import (
    SymbolsDialogJsonMixin,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_layout import (
    SymbolsDialogLayoutMixin,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_rows import (
    SymbolsDialogRowsMixin,
)


class BinaryWorkbenchSymbolsDialog(
    SymbolsDialogJsonMixin,
    SymbolsDialogLayoutMixin,
    SymbolsDialogRowsMixin,
    QDialog,
):
    directoryChanged = Signal(str)
    goToRequested = Signal(int)

    def __init__(
        self,
        variables: dict[str, str],
        equates: dict[str, str],
        labels: dict[str, str],
        libraries: list[BinaryWorkbenchSymbolsDTO] | None = None,
        default_library_name: str = "",
        default_directory: str = "",
        parent=None,
        symbol_offsets: dict[str, list[str]] | None = None,
    ) -> None:
        if parent is None and libraries is not None and not isinstance(libraries, list):
            parent = libraries
            libraries = None
        if parent is None and default_directory and not isinstance(default_directory, str):
            parent = default_directory
            default_directory = ""
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.SYMBOLS_TITLE)
        self.setMinimumSize(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_MIN_WIDTH, BINARY_WORKBENCH_LAYOUT.FILE_DIALOG_MIN_HEIGHT)
        self.setMaximumSize(
            BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_MAX_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_MAX_HEIGHT,
        )
        self.resize(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_WIDTH, BINARY_WORKBENCH_LAYOUT.FILE_DIALOG_HEIGHT)
        self._libraries = {item.name: item for item in libraries or []}
        self._symbols_directory = default_directory
        self._save_requested = False
        self._saved_library_name = ""
        self._saved_library_path = ""
        self._loaded_library_name = ""
        self._loaded_library_path = ""
        self._symbol_offsets = dict(symbol_offsets or {})
        self._rows: list[tuple[QComboBox, QLineEdit, QLineEdit, QWidget, QWidget]] = []
        self._build_dialog(variables, equates, labels, default_library_name)

    def _build_dialog(
        self,
        variables: dict[str, str],
        equates: dict[str, str],
        labels: dict[str, str],
        default_library_name: str,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*ENVIRONMENT_LAYOUT.DIALOG_MARGINS)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(*ENVIRONMENT_LAYOUT.PANEL_MARGINS)
        shell_layout.setSpacing(ENVIRONMENT_LAYOUT.PANEL_SPACING)
        self._build_library_controls(shell_layout, default_library_name)
        self._build_entry(shell_layout)
        self._build_scroll_body(shell_layout)
        self._load_rows(variables, equates, labels)
        self._build_footer_actions(shell_layout)
        layout.addWidget(self.shell, 1)

    def should_save_library(self) -> bool:
        return self._save_requested

    def library_name(self) -> str:
        return ""

    def loaded_library_name(self) -> str:
        return self._loaded_library_name

    def saved_library_name(self) -> str:
        return self._saved_library_name

    def saved_library_path(self) -> str:
        return self._saved_library_path

    def loaded_library_path(self) -> str:
        return self._loaded_library_path
