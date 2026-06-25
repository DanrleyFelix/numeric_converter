from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QTextCursor

from src.core.binary_workbench.editor.commands.custom import (
    create_custom_command,
    selected_command_lines,
)
from src.core.binary_workbench.editor.commands.payloads import (
    command_payload,
    commands_from_context,
    commands_to_context,
)
from src.core.binary_workbench.editor.commands.registry import (
    command_names,
    command_output,
    is_editor_command_line,
)
from src.core.binary_workbench.editor.commands.models import EditorCommand
from src.modules.utils import write_json
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT


class GridCommandsMixin:
    def set_command_directory(self, path: Path | None) -> None:
        self._command_directory = path

    def set_custom_commands(self, commands: dict[str, list[str]]) -> None:
        self._custom_commands = commands_from_context(commands)
        self._refresh_command_completions()

    def custom_commands_context(self) -> dict[str, list[str]]:
        return commands_to_context(self._custom_commands)

    def valid_custom_command_lines(self, lines: list[str]) -> bool:
        return self._valid_custom_command_lines(lines)

    def replace_custom_command(self, name: str, lines: list[str]) -> bool:
        if name not in self._custom_commands or not self._valid_custom_command_lines(lines):
            return False
        command = EditorCommand(name=name, instructions=tuple(lines))
        self._custom_commands = {**self._custom_commands, name: command}
        self._write_custom_command(command)
        self._refresh_command_completions()
        self.commandsChanged.emit(self.custom_commands_context())
        return True

    def remove_custom_command(self, name: str) -> bool:
        if name not in self._custom_commands:
            return False
        self._custom_commands = {
            key: command
            for key, command in self._custom_commands.items()
            if key != name
        }
        self._remove_custom_command_file(name)
        self._refresh_command_completions()
        self.commandsChanged.emit(self.custom_commands_context())
        return True

    def _add_custom_command_from_selection(self, name: str, text: str) -> None:
        lines = selected_command_lines(text)
        if not self._valid_custom_command_lines(lines):
            return
        command = create_custom_command(name, lines)
        if not command.name:
            return
        self._custom_commands = {**self._custom_commands, command.name: command}
        self._write_custom_command(command)
        self._refresh_command_completions()
        self.commandsChanged.emit(self.custom_commands_context())

    def _apply_instruction_command(self, editor) -> bool:
        if editor is not self.instructions:
            return False
        cursor = editor.textCursor()
        block = cursor.block()
        output = command_output(block.text(), self._custom_commands, self._codec)
        if output is None:
            return False
        if not self._command_window_available(editor, block.blockNumber(), len(output)):
            self.commandWarningRequested.emit(BINARY_WORKBENCH_TEXT.STATUS_COMMAND_EMPTY_LINES_REQUIRED)
            return True
        self._replace_command_window(editor, block.blockNumber(), output)
        return True

    def _valid_custom_command_lines(self, lines: list[str]) -> bool:
        if not any(self._codec.instruction_code(line) for line in lines):
            return False
        rows = self._codec.build_source_line_rows(
            lines,
            self._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self._offset_base_text(),
            self._source_rows_start_offset(),
            self._labels,
            self._variables,
            self._equates,
            True,
        )
        return rows is not None and any(row.bytes_text for row in rows)

    def _command_window_available(self, editor, row: int, line_count: int) -> bool:
        if self._edit_rules.allow_byte_shift:
            return True
        lines = editor.toPlainText().split("\n")
        if row + line_count > len(lines):
            return False
        for index in range(row, row + line_count):
            text = lines[index]
            if self._row_offset(index) is None:
                return False
            if index == row and is_editor_command_line(text):
                continue
            if self._codec.instruction_code(text):
                return False
        return True

    def _replace_command_window(self, editor, row: int, lines: list[str]) -> None:
        first = editor.document().findBlockByNumber(row)
        last_row = row if self._edit_rules.allow_byte_shift else row + len(lines) - 1
        last = editor.document().findBlockByNumber(last_row)
        if not first.isValid() or not last.isValid():
            return
        cursor = QTextCursor(editor.document())
        cursor.setPosition(first.position())
        cursor.setPosition(last.position() + len(last.text()), QTextCursor.KeepAnchor)
        cursor.beginEditBlock()
        cursor.insertText("\n".join(lines))
        cursor.endEditBlock()
        editor.setTextCursor(cursor)

    def _refresh_command_completions(self) -> None:
        if hasattr(self, "instructions"):
            self.instructions.set_command_completions(command_names(self._custom_commands, self._codec))

    def _write_custom_command(self, command: EditorCommand) -> None:
        if self._command_directory is None:
            return
        write_json(self._command_directory / f"{command.name}.json", command_payload(command))

    def _remove_custom_command_file(self, name: str) -> None:
        if self._command_directory is None:
            return
        path = self._command_directory / f"{name}.json"
        try:
            path.unlink(missing_ok=True)
        except OSError:
            return
