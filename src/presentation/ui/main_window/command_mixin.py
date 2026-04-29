from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker

from src.modules.utils import COLOR
from src.presentation.ui.components.command_panel.constants import COMMAND_PANEL_TEXT
from src.presentation.ui.main_window.constants import MAIN_WINDOW_TEXT

if TYPE_CHECKING:
    from src.presentation.ui.main_window.window import MainWindow


class MainWindowCommandMixin:

    def _on_converter_input(self: MainWindow, from_type: str, raw_value: str) -> None:
        if self._syncing_converter:
            return

        output = self._converter_presenter.on_user_input(from_type, raw_value)
        if output is None:
            self.footer.set_status(
                self._converter_presenter.last_error_message or MAIN_WINDOW_TEXT.INVALID_CONVERTER_INPUT,
                COLOR.FAILED,
            )
            return

        self._render_converter(output)
        self.footer.set_status(MAIN_WINDOW_TEXT.CONVERTER_UPDATED, COLOR.SUCCESS)
        self._autosave_state()

    def _on_command_text_changed(self: MainWindow) -> None:
        if self._syncing_command:
            return

        text = self.body.command_panel.current_input()
        result = self._command_presenter.on_text_changed(text)

        if self._command_presenter.active_line != text:
            self._syncing_command = True
            with QSignalBlocker(self.body.command_panel.editor):
                self.body.command_panel.set_input_text(self._command_presenter.active_line)
            self._syncing_command = False

        if not self._command_presenter.active_line.strip():
            self.body.command_panel.set_feedback(COMMAND_PANEL_TEXT.IDLE_FEEDBACK, COLOR.INFO)
            self._refresh_command_completions()
            self._autosave_state()
            return

        message = result.message
        if message is None:
            message = (
                MAIN_WINDOW_TEXT.EXPRESSION_READY
                if result.color == COLOR.SUCCESS
                else MAIN_WINDOW_TEXT.EXPRESSION_INCOMPLETE
            )

        self.body.command_panel.set_feedback(message, result.color)
        self._refresh_command_completions()
        self._autosave_state()

    def _on_command_submitted(self: MainWindow) -> None:
        result = self._command_presenter.on_enter()
        self._syncing_command = True
        with QSignalBlocker(self.body.command_panel.editor):
            self.body.command_panel.set_input_text(self._command_presenter.active_line)
        self._syncing_command = False

        self._refresh_workspace_windows()
        self.body.command_panel.set_feedback(
            result.message or MAIN_WINDOW_TEXT.EXPRESSION_INCOMPLETE,
            result.color,
        )

        if result.color == COLOR.SUCCESS and self.body.command_panel.convert_enabled():
            self._convert_command_result()

        self._refresh_command_completions()
        self._autosave_state()

    def _on_key_panel_pressed(self: MainWindow, key: str) -> None:
        if key == "ENTER":
            self._on_command_submitted()
            return

        if key == "CLEAR":
            self._command_presenter.delete("history")
            self._syncing_command = True
            with QSignalBlocker(self.body.command_panel.editor):
                self.body.command_panel.set_input_text(self._command_presenter.active_line)
            self._syncing_command = False
            self._refresh_workspace_windows()
            self.body.command_panel.set_feedback(MAIN_WINDOW_TEXT.DELETED_LAST_ITEM, COLOR.INCOMPLETE)
            self._refresh_command_completions()
            self._autosave_state()
            return

        insertion = self._map_key_panel_input(key)
        current = self._command_presenter.active_line
        self._syncing_command = True
        with QSignalBlocker(self.body.command_panel.editor):
            self.body.command_panel.set_input_text(current + insertion)
        self._syncing_command = False
        self._on_command_text_changed()

    def _convert_command_result(self: MainWindow) -> None:
        raw_result = self._command_presenter.copy_raw()
        if raw_result is None or not raw_result.isdigit():
            self.footer.set_status(MAIN_WINDOW_TEXT.CONVERT_NON_NEGATIVE_ONLY, COLOR.INCOMPLETE)
            return

        output = self._converter_presenter.on_user_input("decimal", raw_result)
        if output is None:
            self.footer.set_status(
                self._converter_presenter.last_error_message or MAIN_WINDOW_TEXT.UNABLE_TO_CONVERT_RESULT,
                COLOR.FAILED,
            )
            return

        self._render_converter(output)
        self.footer.set_status(MAIN_WINDOW_TEXT.COMMAND_RESULT_SENT, COLOR.SUCCESS)

    def _render_converter(self: MainWindow, display_values: dict[str, str]) -> None:
        self._syncing_converter = True
        self.body.converter_panel.set_values(
            self._converter_presenter.raw_inputs,
            display_values,
        )
        self._syncing_converter = False

    def _refresh_command_completions(self: MainWindow) -> None:
        self.body.command_panel.set_completions(self._command_presenter.variable_names)

    def _map_key_panel_input(self: MainWindow, key: str) -> str:
        if key == "x":
            return "*"
        if key == "/":
            return "/"
        if key in {"NOT", "AND", "OR", "XOR"}:
            active_line = self._command_presenter.active_line
            prefix = "" if not active_line or active_line.endswith((" ", "(")) else " "
            return f"{prefix}{key} "
        return key
