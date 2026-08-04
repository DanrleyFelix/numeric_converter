from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFrame, QVBoxLayout

from src.core.binary_workbench.symbol_values import merged_symbol_values
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
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_model import (
    SymbolsTableModel,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_proxy import (
    SymbolsFilterProxyModel,
)


SymbolOffsetsProvider = Callable[[str], tuple[str | None, list[str]]]


class BinaryWorkbenchSymbolsDialog(
    SymbolsDialogJsonMixin,
    SymbolsDialogLayoutMixin,
    SymbolsDialogRowsMixin,
    QDialog,
):
    """Manage local or global symbols through a virtualized table."""

    directoryChanged = Signal(str)
    goToRequested = Signal(int)
    symbolsChanged = Signal(dict)

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
        offsets_provider: SymbolOffsetsProvider | None = None,
    ) -> None:
        """Initialize the dialog without materializing per-symbol widgets."""

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
        self._offsets_provider = offsets_provider
        self._active_offsets_dialog = None
        self._active_offsets_context_id: str | None = None
        symbols = merged_symbol_values(None, variables, equates)
        self.symbols_model = SymbolsTableModel(symbols, self)
        self.symbols_proxy = SymbolsFilterProxyModel(self)
        self.symbols_proxy.setSourceModel(self.symbols_model)
        self._build_dialog()

    def _build_dialog(self) -> None:
        """Build fixed controls around the virtualized symbols table."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*ENVIRONMENT_LAYOUT.DIALOG_MARGINS)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(*ENVIRONMENT_LAYOUT.SYMBOLS_PANEL_MARGINS)
        shell_layout.setSpacing(ENVIRONMENT_LAYOUT.PANEL_SPACING)
        self._build_entry(shell_layout)
        self._build_table(shell_layout)
        self._build_footer_actions(shell_layout)
        layout.addWidget(self.shell, 1)

    def should_save_library(self) -> bool:
        """Return whether this dialog requested library persistence."""

        return self._save_requested

    def library_name(self) -> str:
        """Retain the legacy empty inline-library name contract."""

        return ""

    def loaded_library_name(self) -> str:
        """Return the last successfully loaded library name."""

        return self._loaded_library_name

    def saved_library_name(self) -> str:
        """Return the last successfully saved library name."""

        return self._saved_library_name

    def saved_library_path(self) -> str:
        """Return the last successfully saved library path."""

        return self._saved_library_path

    def loaded_library_path(self) -> str:
        """Return the last successfully loaded library path."""

        return self._loaded_library_path
