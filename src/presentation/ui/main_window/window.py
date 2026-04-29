from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMainWindow, QVBoxLayout, QWidget

from src.application.services.formating_preferences import FormattingPreferencesService
from src.application.services.workspace_state_service import WorkspaceStateService
from src.presentation.presenter.cmd_window_presenter import CommandWindowPresenter
from src.presentation.presenter.converter_presenter import ConverterPresenter
from src.presentation.ui.components import Body, Footer, KeyPanel, Toolbar, WorkspaceTableDialog
from src.presentation.ui.components.help_window import HelpWindow
from src.presentation.ui.components.preferences_dialog import PreferencesDialog
from src.presentation.ui.design.icons import Icons
from src.presentation.ui.helpers.load_qss import STYLESHEET
from src.presentation.ui.main_window.constants import (
    MAIN_WINDOW_MARGIN,
    MAIN_WINDOW_SIZE,
    MAIN_WINDOW_SPACING,
    MAIN_WINDOW_TEXT,
)
from src.presentation.ui.main_window.command_mixin import MainWindowCommandMixin
from src.presentation.ui.main_window.state_mixin import MainWindowStateMixin
from src.presentation.ui.main_window.workspace_mixin import MainWindowWorkspaceMixin


class MainWindow(
    MainWindowWorkspaceMixin,
    MainWindowStateMixin,
    MainWindowCommandMixin,
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

    def _build_ui(self) -> None:
        self.toolbar = Toolbar()
        self.body = Body()
        self.key_panel = KeyPanel()
        self.footer = Footer()

        container = QWidget()
        layout_container = QVBoxLayout(container)
        layout_container.setContentsMargins(
            MAIN_WINDOW_MARGIN.CONTAINER_LEFT,
            MAIN_WINDOW_MARGIN.CONTAINER_TOP,
            MAIN_WINDOW_MARGIN.CONTAINER_RIGHT,
            MAIN_WINDOW_MARGIN.CONTAINER_BOTTOM,
        )
        layout_container.setSpacing(MAIN_WINDOW_SPACING.CONTAINER)
        layout_container.addWidget(self.body, 1)
        layout_container.addWidget(self.key_panel)
        layout_container.addWidget(self.footer)
        layout_container.addStretch()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(
            MAIN_WINDOW_MARGIN.CENTRAL_LEFT,
            MAIN_WINDOW_MARGIN.CENTRAL_TOP,
            MAIN_WINDOW_MARGIN.CENTRAL_RIGHT,
            MAIN_WINDOW_MARGIN.CENTRAL_BOTTOM,
        )
        layout.setSpacing(MAIN_WINDOW_SPACING.CENTRAL)
        layout.addWidget(self.toolbar)
        layout.addWidget(container, 1)
        layout.addStretch()
        central.setObjectName("main-window")

        self.setCentralWidget(central)

    def _bind_events(self) -> None:
        self.body.converter_panel.inputEdited.connect(self._on_converter_input)
        self.body.command_panel.editor.textChanged.connect(self._on_command_text_changed)
        self.body.command_panel.editor.submitted.connect(self._on_command_submitted)
        self.key_panel.keyPressed.connect(self._on_key_panel_pressed)

        self.toolbar.save_workspace_action.triggered.connect(self._save_workspace)
        self.toolbar.load_workspace_action.triggered.connect(self._load_workspace)
        self.toolbar.converter_preferences_action.triggered.connect(self._open_preferences)
        self.toolbar.toggle_key_panel_action.toggled.connect(self._on_key_panel_toggled)
        self.toolbar.help_button.clicked.connect(self._open_help)
        self.body.command_panel.show_logs_button.clicked.connect(self._open_logs_window)
        self.body.command_panel.show_variables_button.clicked.connect(self._open_variables_window)

    def _on_key_panel_toggled(self, visible: bool) -> None:
        self.key_panel.setVisible(visible)
        self._update_minimum_height(visible)
        self._autosave_state()

    def _update_minimum_height(self, key_panel_visible: bool) -> None:
        min_height = MAIN_WINDOW_SIZE.MIN_HEIGHT
        if not key_panel_visible:
            reduction = int(
                self.key_panel.sizeHint().height()
                * MAIN_WINDOW_SIZE.KEY_PANEL_HIDDEN_REDUCTION_RATIO
            )
            min_height = max(360, MAIN_WINDOW_SIZE.MIN_HEIGHT - reduction)
        self.setMinimumSize(MAIN_WINDOW_SIZE.MIN_WIDTH, min_height)

    def _save_workspace(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            MAIN_WINDOW_TEXT.SAVE_WORKSPACE_TITLE,
            str(self._state_service.workspace_directory / MAIN_WINDOW_TEXT.WORKSPACE_FILENAME),
            MAIN_WINDOW_TEXT.FILE_FILTER,
        )
        if not path:
            return
        saved_path = self._state_service.save_workspace(self._collect_context(), Path(path))
        self.footer.set_status(
            MAIN_WINDOW_TEXT.WORKSPACE_SAVED_TEMPLATE.format(name=saved_path.name)
        )

    def _load_workspace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            MAIN_WINDOW_TEXT.LOAD_WORKSPACE_TITLE,
            str(self._state_service.workspace_directory),
            MAIN_WINDOW_TEXT.FILE_FILTER,
        )
        if not path:
            return
        workspace = self._state_service.load_workspace(Path(path))
        self._apply_context(workspace.context)
        self._refresh_command_completions()
        self.footer.set_status(
            MAIN_WINDOW_TEXT.WORKSPACE_LOADED_TEMPLATE.format(name=Path(path).name)
        )
        self._autosave_state()

    def _open_preferences(self) -> None:
        dialog = PreferencesDialog(
            formatting=self._preferences_service.get_format(),
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        formatting = dialog.selected_formatting()
        for key, config in formatting.items():
            self._preferences_service.update(key, config)

        output = self._converter_presenter.update_formatting(formatting)
        if output is not None:
            self._render_converter(output)

        self.footer.set_status(MAIN_WINDOW_TEXT.PREFERENCES_UPDATED)
        self._autosave_state()

    def _open_help(self) -> None:
        if self._help_window is None:
            self._help_window = HelpWindow(self)
            self._help_window.destroyed.connect(lambda *_: self._clear_help_window())

        self._help_window.show()
        self._help_window.raise_()
        self._help_window.activateWindow()

    def _clear_help_window(self) -> None:
        self._help_window = None
