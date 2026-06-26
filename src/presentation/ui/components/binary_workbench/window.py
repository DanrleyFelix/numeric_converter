from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QLabel, QMainWindow

from src.modules.application_dtos import ProgramContextDTO
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchStateDTO,
)
from src.modules.shared_dtos import WindowSizeDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.tabs import BinaryWorkbenchTabs
from src.presentation.ui.components.binary_workbench.toolbar import BinaryWorkbenchToolbar
from src.presentation.ui.components.binary_workbench.window_close_flow import (
    BinaryWorkbenchWindowCloseMixin,
)
from src.presentation.ui.components.binary_workbench.window_environment_actions import (
    BinaryWorkbenchWindowEnvironmentMixin,
)
from src.presentation.ui.components.binary_workbench.window_file_actions import (
    BinaryWorkbenchWindowFileActionsMixin,
)
from src.presentation.ui.components.binary_workbench.window_layout_actions import (
    BinaryWorkbenchWindowLayoutMixin,
)
from src.presentation.ui.components.binary_workbench.window_search_actions import (
    BinaryWorkbenchWindowSearchMixin,
)
from src.presentation.ui.components.binary_workbench.window_version_actions import (
    BinaryWorkbenchWindowVersionMixin,
)
from src.presentation.ui.components.binary_workbench.window_workspace_configuration_actions import (
    BinaryWorkbenchWindowWorkspaceConfigurationMixin,
)
from src.presentation.ui.components.help_window import HelpWindow
from src.presentation.ui.components.help_window.pages.binary_workbench import (
    BINARY_WORKBENCH_HELP_PAGES,
)
from src.presentation.ui.helpers.load_qss import STYLESHEET


class BinaryWorkbenchWindow(
    BinaryWorkbenchWindowLayoutMixin,
    BinaryWorkbenchWindowFileActionsMixin,
    BinaryWorkbenchWindowEnvironmentMixin,
    BinaryWorkbenchWindowWorkspaceConfigurationMixin,
    BinaryWorkbenchWindowSearchMixin,
    BinaryWorkbenchWindowVersionMixin,
    BinaryWorkbenchWindowCloseMixin,
    QMainWindow,
):
    sizePersistRequested = Signal(int, int)
    stateChanged = Signal(object)
    preferencesChanged = Signal(object)
    programContextChanged = Signal(object)

    def __init__(
        self,
        state: BinaryWorkbenchStateDTO,
        workspace_directory: Path | None = None,
        preferences: BinaryWorkbenchPreferencesDTO | None = None,
        program_context: ProgramContextDTO | None = None,
    ):
        super().__init__()
        self.setObjectName("binary-workbench-window")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.TITLE)
        self.setMinimumSize(BINARY_WORKBENCH_LAYOUT.MIN_WIDTH, BINARY_WORKBENCH_LAYOUT.MIN_HEIGHT)
        self.resize(BINARY_WORKBENCH_LAYOUT.WINDOW_WIDTH, BINARY_WORKBENCH_LAYOUT.WINDOW_HEIGHT)
        self.toolbar = BinaryWorkbenchToolbar()
        self._help_window: HelpWindow | None = None
        self.tabs = BinaryWorkbenchTabs(
            state,
            workspace_directory,
            preferences,
            program_context,
        )
        self.footer_status = QLabel(BINARY_WORKBENCH_TEXT.STATUS_IDLE, self)
        self.footer_status.setObjectName("binary-workbench-footer-status")
        self.statusBar().hide()
        self.tabs.statusChanged.connect(self._show_status)
        self.tabs.statusWarningChanged.connect(self._show_warning_status)
        self.tabs.stateChanged.connect(self.stateChanged.emit)
        self.tabs.preferencesChanged.connect(self.preferencesChanged.emit)
        self.tabs.programContextChanged.connect(self.programContextChanged.emit)
        self.tabs.closeRequested.connect(self._request_tab_close)
        self._connect_actions()
        self._build_ui()
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_IDLE)

    def export_state(self) -> BinaryWorkbenchStateDTO:
        state = self.tabs.export_state()
        return BinaryWorkbenchStateDTO(
            **{
                **state.__dict__,
                "window_size": WindowSizeDTO(width=self.width(), height=self.height()),
            }
        )

    def load_state(self, state: BinaryWorkbenchStateDTO) -> None:
        self.tabs.load_state(state)

    def open_binary_path(self, path: Path) -> None:
        self.tabs.open_binary_path(path)

    def open_file_path(self, path: Path) -> None:
        self.tabs.open_file_path(path)

    def open_assembly_path(self, path: Path) -> None:
        self.tabs.open_assembly_path(path)

    def open_workspace_path(self, path: Path) -> bool:
        return self.tabs.open_workspace_path(path)

    def new_scratch_tab(self) -> None:
        self.tabs.new_scratch_tab()

    def open_guide(self) -> None:
        if self._help_window is None:
            self._help_window = HelpWindow(self, BINARY_WORKBENCH_HELP_PAGES)
            self._help_window.setWindowIcon(self.windowIcon())
            self._help_window.setStyleSheet(STYLESHEET)
            self._help_window.destroyed.connect(lambda: setattr(self, "_help_window", None))
        self._help_window.show()
        self._help_window.raise_()
        self._help_window.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.tabs.flush_search_cache()
        self.sizePersistRequested.emit(self.width(), self.height())
        super().closeEvent(event)

    def _show_status(self, message: str, timeout: int = 0, error: bool = False) -> None:
        self._set_status(message, timeout, "error" if error else "ready")

    def _show_warning_status(self, message: str) -> None:
        self._set_status(message, 0, "warning")

    def _set_status(self, message: str, timeout: int, kind: str) -> None:
        self.footer_status.setProperty("statusKind", kind)
        self.footer_status.style().unpolish(self.footer_status)
        self.footer_status.style().polish(self.footer_status)
        self.footer_status.setText(message)
        self.statusBar().showMessage(message, timeout)

    def _placeholder_actions(self):
        return ()
