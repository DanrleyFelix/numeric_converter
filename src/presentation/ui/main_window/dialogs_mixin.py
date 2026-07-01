from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from src.modules.utils import read_json
from src.presentation.repository.binary_workbench_workspace.constants import SCHEMA_VERSION
from src.presentation.ui.components import BinaryWorkbenchWindow
from src.presentation.ui.components.donor import DonorWindow
from src.presentation.ui.components.help_window import HelpWindow
from src.presentation.ui.components.preferences_dialog import LogPreferencesDialog, PreferencesDialog
from src.presentation.ui.helpers.load_qss import STYLESHEET
from src.presentation.ui.helpers.window_geometry import ensure_window_on_available_screen
from src.presentation.ui.main_window.constants import MAIN_WINDOW_STATE, MAIN_WINDOW_TEXT

if TYPE_CHECKING:
    from src.presentation.ui.main_window.window import MainWindow


class MainWindowDialogsMixin:
    def _open_binary_workbench(self: MainWindow) -> None:
        if self._binary_workbench_window is None:
            self._binary_workbench_window = BinaryWorkbenchWindow(
                self._binary_workbench_state,
                self._state_service.binary_workspace_directory,
                self._binary_workbench_preferences,
                self._program_context,
            )
            self._binary_workbench_window.setWindowIcon(self.windowIcon())
            self._binary_workbench_window.setStyleSheet(STYLESHEET)
            self._binary_workbench_window.stateChanged.connect(
                self._remember_binary_workbench_state
            )
            self._binary_workbench_window.preferencesChanged.connect(
                self._remember_binary_workbench_preferences
            )
            self._binary_workbench_window.programContextChanged.connect(
                self._remember_program_context
            )
            self._binary_workbench_window.sizePersistRequested.connect(
                lambda width, height: self._remember_window_size(
                    MAIN_WINDOW_STATE.BINARY_WORKBENCH_WINDOW_KEY,
                    width,
                    height,
                )
            )
            self._binary_workbench_window.destroyed.connect(
                lambda *_: self._clear_binary_workbench_window()
            )
            if self._binary_workbench_state.window_size is not None:
                self._binary_workbench_window.resize(
                    self._binary_workbench_state.window_size.width,
                    self._binary_workbench_state.window_size.height,
                )
        else:
            self._binary_workbench_window.load_state(self._binary_workbench_state)

        if self._binary_workbench_window.windowState() & Qt.WindowMinimized:
            self._binary_workbench_window.setWindowState(
                self._binary_workbench_window.windowState() & ~Qt.WindowMinimized
            )
        ensure_window_on_available_screen(self._binary_workbench_window, self)
        self._binary_workbench_window.show()
        ensure_window_on_available_screen(self._binary_workbench_window, self)
        self._binary_workbench_window.raise_()
        self._binary_workbench_window.activateWindow()
        self.footer.set_status(MAIN_WINDOW_TEXT.BINARY_WORKBENCH_READY)

    def _open_donor(self: MainWindow) -> None:
        if self._donor_window is None:
            self._donor_window = DonorWindow()
            self._donor_window.setWindowIcon(self.windowIcon())
            self._donor_window.setStyleSheet(STYLESHEET)
            self._donor_window.destroyed.connect(lambda *_: self._clear_donor_window())

        if self._donor_window.windowState() & Qt.WindowMinimized:
            self._donor_window.setWindowState(self._donor_window.windowState() & ~Qt.WindowMinimized)
        ensure_window_on_available_screen(self._donor_window, self)
        self._donor_window.show()
        ensure_window_on_available_screen(self._donor_window, self)
        self._donor_window.raise_()
        self._donor_window.activateWindow()

    def _save_workspace(self: MainWindow) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            MAIN_WINDOW_TEXT.SAVE_WORKSPACE_TITLE,
            str(self._state_service.workspace_directory / MAIN_WINDOW_TEXT.WORKSPACE_FILENAME),
            MAIN_WINDOW_TEXT.FILE_FILTER,
        )
        if not path:
            return
        if self._binary_workbench_window is not None and self._binary_workbench_window.tabs.current_context() is not None:
            if self._binary_workbench_window.tabs.save_current_workspace(Path(path)):
                self.footer.set_status(
                    MAIN_WINDOW_TEXT.WORKSPACE_SAVED_TEMPLATE.format(name=Path(path).name)
                )
                self._autosave_state()
                return
        saved_path = self._state_service.save_workspace(self._collect_context(), Path(path))
        self.footer.set_status(
            MAIN_WINDOW_TEXT.WORKSPACE_SAVED_TEMPLATE.format(name=saved_path.name)
        )

    def _load_workspace(self: MainWindow) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            MAIN_WINDOW_TEXT.LOAD_WORKSPACE_TITLE,
            str(self._state_service.workspace_directory),
            MAIN_WINDOW_TEXT.FILE_FILTER,
        )
        if not path:
            return
        payload = read_json(Path(path))
        if payload and payload.get("schema_version") == SCHEMA_VERSION:
            self._open_binary_workbench()
            if self._binary_workbench_window is not None and self._binary_workbench_window.open_workspace_path(Path(path)):
                self.footer.set_status(
                    MAIN_WINDOW_TEXT.WORKSPACE_LOADED_TEMPLATE.format(name=Path(path).name)
                )
                self._autosave_state()
                return
        workspace = self._state_service.load_workspace(Path(path))
        self._apply_context(workspace.context)
        self._refresh_command_completions()
        self.footer.set_status(
            MAIN_WINDOW_TEXT.WORKSPACE_LOADED_TEMPLATE.format(name=Path(path).name)
        )
        self._autosave_state()

    def _open_preferences(self: MainWindow) -> None:
        preferences = self._preferences_service.get_preferences()
        dialog = PreferencesDialog(
            formatting=preferences.formatters,
            default_copy_field=preferences.default_copy_field,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        formatting = dialog.selected_formatting()
        for key, config in formatting.items():
            self._preferences_service.update(key, config)
        self._preferences_service.update_default_copy_field(
            dialog.selected_default_copy_field()
        )

        output = self._converter_presenter.update_formatting(formatting)
        if output is not None:
            self._render_converter(output)

        self.footer.set_status(MAIN_WINDOW_TEXT.PREFERENCES_UPDATED)
        self._autosave_state()

    def _open_log_preferences(self: MainWindow) -> None:
        dialog = LogPreferencesDialog(
            preferences=self._preferences_service.get_preferences().log_preferences,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        preferences = dialog.selected_preferences()
        self._preferences_service.update_log_preferences(preferences)
        self._command_presenter.set_log_preferences(preferences)
        self.footer.set_status(MAIN_WINDOW_TEXT.PREFERENCES_UPDATED)
        self._autosave_state()

    def _open_help(self: MainWindow) -> None:
        if self._help_window is None:
            self._help_window = HelpWindow()
            self._help_window.setWindowIcon(self.windowIcon())
            self._help_window.setStyleSheet(STYLESHEET)
            self._help_window.sizePersistRequested.connect(
                lambda width, height: self._remember_window_size(
                    MAIN_WINDOW_STATE.HELP_WINDOW_KEY,
                    width,
                    height,
                )
            )
            self._help_window.destroyed.connect(lambda *_: self._clear_help_window())
            self._restore_window_size(MAIN_WINDOW_STATE.HELP_WINDOW_KEY, self._help_window)

        if self._help_window.windowState() & Qt.WindowMinimized:
            self._help_window.setWindowState(
                self._help_window.windowState() & ~Qt.WindowMinimized
            )
        ensure_window_on_available_screen(self._help_window, self)
        self._help_window.show()
        ensure_window_on_available_screen(self._help_window, self)
        self._help_window.raise_()
        self._help_window.activateWindow()

    def _clear_help_window(self: MainWindow) -> None:
        self._help_window = None

    def _clear_binary_workbench_window(self: MainWindow) -> None:
        self._binary_workbench_window = None

    def _clear_donor_window(self: MainWindow) -> None:
        self._donor_window = None
