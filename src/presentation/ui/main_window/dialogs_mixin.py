from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog

from src.presentation.ui.components.help_window import HelpWindow
from src.presentation.ui.components.preferences_dialog import PreferencesDialog
from src.presentation.ui.main_window.constants import MAIN_WINDOW_TEXT

if TYPE_CHECKING:
    from src.presentation.ui.main_window.window import MainWindow


class MainWindowDialogsMixin:
    def _save_workspace(self: MainWindow) -> None:
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

    def _load_workspace(self: MainWindow) -> None:
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

    def _open_preferences(self: MainWindow) -> None:
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

    def _open_help(self: MainWindow) -> None:
        if self._help_window is None:
            self._help_window = HelpWindow(self)
            self._help_window.destroyed.connect(lambda *_: self._clear_help_window())

        self._help_window.show()
        self._help_window.raise_()
        self._help_window.activateWindow()

    def _clear_help_window(self: MainWindow) -> None:
        self._help_window = None
