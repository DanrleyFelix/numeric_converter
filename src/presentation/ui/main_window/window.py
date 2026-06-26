from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow

from src.modules.application_dtos import ProgramContextDTO
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchPreferencesDTO,
    BinaryWorkbenchStateDTO,
)
from src.modules.services import (
    BinaryWorkbenchPreferencesService,
    FormattingPreferencesService,
    WorkspaceStateService,
)
from src.presentation.presenter.cmd_window_presenter import CommandWindowPresenter
from src.presentation.presenter.converter_presenter import ConverterPresenter
from src.presentation.ui.components import BinaryWorkbenchWindow, WorkspaceTableDialog
from src.presentation.ui.components.donor import DonorWindow
from src.presentation.ui.components.help_window import HelpWindow
from src.presentation.ui.design.icons import Icons
from src.presentation.ui.helpers.load_qss import STYLESHEET
from src.presentation.ui.main_window.constants import MAIN_WINDOW_SIZE, MAIN_WINDOW_TEXT
from src.presentation.ui.main_window.command_mixin import MainWindowCommandMixin
from src.presentation.ui.main_window.dialogs_mixin import MainWindowDialogsMixin
from src.presentation.ui.main_window.layout_mixin import MainWindowLayoutMixin
from src.presentation.ui.main_window.state_mixin import MainWindowStateMixin
from src.presentation.ui.main_window.workspace_mixin import MainWindowWorkspaceMixin


class MainWindow(
    MainWindowWorkspaceMixin,
    MainWindowStateMixin,
    MainWindowCommandMixin,
    MainWindowDialogsMixin,
    MainWindowLayoutMixin,
    QMainWindow,
):

    def __init__(
        self,
        converter_presenter: ConverterPresenter,
        command_presenter: CommandWindowPresenter,
        state_service: WorkspaceStateService,
        preferences_service: FormattingPreferencesService,
        binary_preferences_service: BinaryWorkbenchPreferencesService,
    ):
        super().__init__()
        self._converter_presenter = converter_presenter
        self._command_presenter = command_presenter
        self._state_service = state_service
        self._preferences_service = preferences_service
        self._binary_preferences_service = binary_preferences_service
        self._binary_workbench_state = BinaryWorkbenchStateDTO()
        self._program_context = ProgramContextDTO()
        self._binary_workbench_preferences = BinaryWorkbenchPreferencesDTO()
        self._help_window: HelpWindow | None = None
        self._binary_workbench_window: BinaryWorkbenchWindow | None = None
        self._donor_window: DonorWindow | None = None
        self._logs_window: WorkspaceTableDialog | None = None
        self._variables_window: WorkspaceTableDialog | None = None
        self._auto_convert_enabled = False
        self._size_before_key_panel_show: QSize | None = None
        self._window_sizes = {}
        self._syncing_converter = False
        self._syncing_command = False
        self._loaded = False

        self.setMinimumSize(MAIN_WINDOW_SIZE.MIN_WIDTH, MAIN_WINDOW_SIZE.MIN_HEIGHT)
        self.setWindowTitle(MAIN_WINDOW_TEXT.TITLE)
        self.setWindowIcon(Icons.hexadecimal())

        self._build_ui()
        self.setStyleSheet(STYLESHEET)

        self._bind_events()
        self._load_default_state()
        self.body.focus_decimal()
        self._loaded = True

    def closeEvent(self, event: QCloseEvent) -> None:
        for window in (
            self._help_window,
            self._binary_workbench_window,
            self._donor_window,
            self._logs_window,
            self._variables_window,
        ):
            if window is not None:
                window.close()
        self._autosave_state()
        super().closeEvent(event)
