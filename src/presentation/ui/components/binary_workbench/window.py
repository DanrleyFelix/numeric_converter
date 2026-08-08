from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeyEvent, QKeySequence, QResizeEvent, QShortcut
from PySide6.QtWidgets import QLabel, QMainWindow

from src.modules.application_dtos import ProgramContextDTO
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.modules.shared_dtos import WindowSizeDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.tabs import BinaryWorkbenchTabs
from src.presentation.ui.components.binary_workbench.tabs.recovery import merge_recovery_tabs
from src.presentation.ui.components.binary_workbench.toolbar import BinaryWorkbenchToolbar
from src.presentation.ui.components.binary_workbench.window_close_flow import (
    BinaryWorkbenchWindowCloseMixin,
)
from src.presentation.ui.components.binary_workbench.debugger.window_actions import (
    BinaryWorkbenchDebuggerMixin,
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
from src.presentation.ui.helpers.window_geometry import ensure_window_on_available_screen


class BinaryWorkbenchWindow(
    BinaryWorkbenchDebuggerMixin,
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
        recovery_omitted_tabs: tuple[BinaryWorkbenchTabContextDTO, ...] = (),
    ):
        super().__init__()
        self.setObjectName("binary-workbench-window")
        self.setStyleSheet(STYLESHEET)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.TITLE)
        self.setMinimumSize(BINARY_WORKBENCH_LAYOUT.MIN_WIDTH, BINARY_WORKBENCH_LAYOUT.MIN_HEIGHT)
        self.resize(BINARY_WORKBENCH_LAYOUT.WINDOW_WIDTH, BINARY_WORKBENCH_LAYOUT.WINDOW_HEIGHT)
        self.toolbar = BinaryWorkbenchToolbar()
        self._recovery_omitted_tabs = recovery_omitted_tabs
        self._help_window: HelpWindow | None = None
        self._hazards_window = None
        self.tabs = BinaryWorkbenchTabs(
            state,
            workspace_directory,
            preferences,
            program_context,
        )
        self._recalculate_shortcut = QShortcut(QKeySequence("F1"), self)
        self._recalculate_shortcut.setObjectName("binary-workbench-recalculate-shortcut")
        self._recalculate_shortcut.activated.connect(self._recalculate_current_source)
        self._initialize_debugger_support()
        self.footer_status = QLabel(BINARY_WORKBENCH_TEXT.STATUS_IDLE, self)
        self.footer_status.setObjectName("binary-workbench-footer-status")
        self.statusBar().hide()
        self.tabs.statusChanged.connect(self._show_status)
        self.tabs.statusWarningChanged.connect(self._show_warning_status)
        self.tabs.statusErrorChanged.connect(lambda message: self._show_status(message, 0, True))
        self.tabs.stateChanged.connect(self._emit_recovery_safe_state)
        self.tabs.preferencesChanged.connect(self.preferencesChanged.emit)
        self.tabs.programContextChanged.connect(self.programContextChanged.emit)
        self.tabs.closeRequested.connect(self._request_tab_close)
        self.tabs.currentChanged.connect(lambda _: self._apply_responsive_layout())
        self._connect_actions()
        self._build_ui()
        self._apply_responsive_layout()
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_IDLE)

    def export_state(self) -> BinaryWorkbenchStateDTO:
        state = merge_recovery_tabs(
            self.tabs.export_state(),
            self._recovery_omitted_tabs,
        )
        return BinaryWorkbenchStateDTO(
            **{
                **state.__dict__,
                "window_size": WindowSizeDTO(width=self.width(), height=self.height()),
            }
        )

    def load_state(self, state: BinaryWorkbenchStateDTO) -> None:
        self._recovery_omitted_tabs = ()
        self.tabs.load_state(state)

    def _emit_recovery_safe_state(self, state: BinaryWorkbenchStateDTO) -> None:
        """Keep skipped startup payloads persisted without creating their pages."""

        self.stateChanged.emit(merge_recovery_tabs(state, self._recovery_omitted_tabs))

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
        ensure_window_on_available_screen(self._help_window, self)
        self._help_window.show()
        ensure_window_on_available_screen(self._help_window, self)
        self._help_window.raise_()
        self._help_window.activateWindow()

    def _recalculate_current_source(self) -> None:
        """Refresh labels and branches around the active editor viewport."""

        page = self.tabs.currentWidget()
        grid = getattr(page, "grid", None)
        if grid is not None:
            grid.recalculate_labels_and_branches()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            event.key() == Qt.Key_H
            and bool(event.modifiers() & Qt.AltModifier)
            and not bool(event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier | Qt.MetaModifier))
        ):
            self._open_hazards()
            event.accept()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Update width-dependent editor columns while preserving preferences."""

        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        """Hide Bytes at narrow widths on the currently visible editor page."""

        page = self.tabs.currentWidget()
        if page is None or not hasattr(page, "set_responsive_bytes_hidden"):
            return
        page.set_responsive_bytes_hidden(
            self.width() < BINARY_WORKBENCH_LAYOUT.RESPONSIVE_BYTES_HIDE_WIDTH
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._close_debugger_windows():
            event.ignore()
            return
        self.tabs.flush_open_workspaces()
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
