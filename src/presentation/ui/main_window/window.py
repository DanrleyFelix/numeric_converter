from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from src.application.services.formating_preferences import FormattingPreferencesService
from src.application.services.workspace_state_service import WorkspaceStateService
from src.presentation.presenter.cmd_window_presenter import CommandWindowPresenter
from src.presentation.presenter.converter_presenter import ConverterPresenter
from src.presentation.ui.components import WorkspaceTableDialog
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
    ):
        super().__init__()
        self._converter_presenter = converter_presenter
        self._command_presenter = command_presenter
        self._state_service = state_service
        self._preferences_service = preferences_service
        self._help_window: HelpWindow | None = None
        self._logs_window: WorkspaceTableDialog | None = None
        self._variables_window: WorkspaceTableDialog | None = None
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
        self._loaded = True

    def closeEvent(self, event):
        self._autosave_state()
        super().closeEvent(event)
