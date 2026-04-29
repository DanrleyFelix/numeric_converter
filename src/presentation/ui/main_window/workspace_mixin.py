from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from src.modules.utils import COLOR
from src.presentation.ui.components import WorkspaceRow, WorkspaceTableDialog
from src.presentation.ui.components.workspace_table.constants import (
    WORKSPACE_TABLE_HEADERS,
    WORKSPACE_TABLE_TEXT,
)
from src.presentation.ui.main_window.constants import MAIN_WINDOW_TEXT

if TYPE_CHECKING:
    from src.presentation.ui.main_window.window import MainWindow


class MainWindowWorkspaceMixin:

    def _open_logs_window(self: MainWindow) -> None:
        self._logs_window = self._ensure_workspace_window(
            window=self._logs_window,
            title=WORKSPACE_TABLE_TEXT.LOGS_TITLE,
            headers=WORKSPACE_TABLE_HEADERS["logs"],
            clear_callback=self._clear_logs_window,
            remove_callback=self._remove_log_row,
        )
        self._refresh_logs_window()
        self._present_workspace_window(self._logs_window)

    def _open_variables_window(self: MainWindow) -> None:
        self._variables_window = self._ensure_workspace_window(
            window=self._variables_window,
            title=WORKSPACE_TABLE_TEXT.VARIABLES_TITLE,
            headers=WORKSPACE_TABLE_HEADERS["variables"],
            clear_callback=self._clear_variables_window,
            remove_callback=self._remove_variable_row,
        )
        self._refresh_variables_window()
        self._present_workspace_window(self._variables_window)

    def _clear_logs_window(self: MainWindow) -> None:
        self._logs_window = None

    def _clear_variables_window(self: MainWindow) -> None:
        self._variables_window = None

    def _remove_log_row(self: MainWindow, index: object) -> None:
        try:
            row_index = int(index)
        except (TypeError, ValueError):
            return
        self._command_presenter.remove_log(row_index)
        self._refresh_workspace_windows()
        self.footer.set_status(MAIN_WINDOW_TEXT.LOG_REMOVED, COLOR.INCOMPLETE)
        self._autosave_state()

    def _remove_variable_row(self: MainWindow, name: object) -> None:
        if not isinstance(name, str):
            return
        self._command_presenter.remove_variable(name)
        self._refresh_workspace_windows()
        self._refresh_command_completions()
        self.footer.set_status(
            MAIN_WINDOW_TEXT.VARIABLE_REMOVED_TEMPLATE.format(name=name),
            COLOR.INCOMPLETE,
        )
        self._autosave_state()

    def _refresh_workspace_windows(self: MainWindow) -> None:
        self._refresh_logs_window()
        self._refresh_variables_window()

    def _ensure_workspace_window(
        self: MainWindow,
        window: WorkspaceTableDialog | None,
        title: str,
        headers: Sequence[str],
        clear_callback: Callable[[], None],
        remove_callback: Callable[[object], None],
    ) -> WorkspaceTableDialog:
        if window is None:
            window = WorkspaceTableDialog(title, list(headers), self)
            window.destroyed.connect(lambda *_: clear_callback())
            window.removeRequested.connect(remove_callback)
        return window

    def _present_workspace_window(self: MainWindow, window: WorkspaceTableDialog | None) -> None:
        if window is None:
            return
        window.show()
        window.raise_()
        window.activateWindow()

    def _refresh_logs_window(self: MainWindow) -> None:
        if self._logs_window is None:
            return
        self._logs_window.set_rows(
            [
                WorkspaceRow(key=index, values=(instruction, result))
                for index, instruction, result in self._command_presenter.workspace_log_rows
            ]
        )

    def _refresh_variables_window(self: MainWindow) -> None:
        if self._variables_window is None:
            return
        self._variables_window.set_rows(
            [
                WorkspaceRow(key=name, values=(name, value, hex_value))
                for name, value, hex_value in self._command_presenter.workspace_variable_detail_rows
            ]
        )
