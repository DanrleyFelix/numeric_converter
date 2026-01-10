from typing import Optional
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCursor, QKeyEvent
from PySide6.QtCore import Qt

from src.application.contracts.cmd_window_contract import ICommandWindowPresenter


class CommandWindow(QTextEdit):

    def __init__(self, presenter: ICommandWindowPresenter):
        super().__init__()
        self._presenter: ICommandWindowPresenter = presenter
        self._input_anchor: int = 0

        self.setAcceptRichText(True)
        self.setUndoRedoEnabled(True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._execute_current_line()
            return

        if not self._is_cursor_in_input_zone():
            self._force_cursor_to_input_zone()

        super().keyPressEvent(event)

    def _is_cursor_in_input_zone(self) -> bool:
        return self.textCursor().position() >= self._input_anchor

    def _force_cursor_to_input_zone(self) -> None:
        cursor = self.textCursor()
        cursor.setPosition(self.document().characterCount() - 1)
        self.setTextCursor(cursor)

    def _execute_current_line(self) -> None:
        command = self._current_command().strip()

        self.append("")  # fecha linha do comando

        result = self._presenter.on_command(command)

        if result is not None:
            self._append_result(result)

        self.append("")  # linha em branco (UX MATLAB)

        self._reset_input_zone()

    def _current_command(self) -> str:
        cursor = self.textCursor()
        cursor.setPosition(self._input_anchor)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        return cursor.selectedText()

    def _append_result(self, view_model) -> None:
        """
        Aqui entra o renderer (HTML / syntax highlight).
        O command window só insere.
        """
        html = self._render(view_model)
        self.insertHtml(html)
        self.insertPlainText("\n")

    def _render(self, view_model) -> str:
        # placeholder: renderer dedicado cuida disso
        return "<span>resultado</span>"

    def _reset_input_zone(self) -> None:
        self._input_anchor = self.document().characterCount() - 1
        self.document().clearUndoRedoStacks()
