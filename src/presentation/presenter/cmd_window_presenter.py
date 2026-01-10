from typing import Optional, List
from numbers import Number

from src.application.contracts.cmd_window_contract import ICommandWindowController
from src.application.contracts.preferences_contract import IOutputFormatter
from src.presentation.formatters.clean_formatter import CleanFormatter
from src.application.dto.command_render_result import CommandRenderResultDTO
from src.application.dto.command_entry import CommandEntryDTO
from src.application.dto.command_entry import CommandLogEntryDTO
from src.presentation.presenter.utils import Limit

from src.modules.utils import COLOR


class CommandWindowPresenter:

    def __init__(
        self,
        controller: ICommandWindowController,
        formatter: IOutputFormatter):

        self._controller = controller
        self._formatter = formatter
        self._clean_formatter = CleanFormatter()

        self._history: List[CommandEntryDTO] = []
        self._active_line: str = ""
        self._log: List[CommandLogEntryDTO] = []

        self._undo_stack: List[str] = []
        self._redo_stack: List[str] = []

        self._last_validation_state: bool = False
        self._last_result_raw: Optional[Number] = None
        self._last_result_formatted: Optional[str] = None

    @property
    def history(self) -> List[CommandEntryDTO]:
        return list(self._history)
    
    @property
    def log(self) -> List[CommandLogEntryDTO]:
        return list(self._log)

    @property
    def active_line(self) -> str:
        return self._active_line

    def on_text_changed(self, new_text: str, pasted: bool = False) -> CommandRenderResultDTO:
        try:
            validation_state = self._controller.on_input_changed(new_text)
            if new_text != self._active_line:
                self._undo_stack.append(self._active_line)
                self._redo_stack.clear()
            self._active_line = new_text
            self._last_validation_state = validation_state
            color = COLOR.SUCCESS if validation_state else COLOR.INCOMPLETE
            return CommandRenderResultDTO(lines=[new_text], color=color)

        except Exception:
            if pasted:
                self._active_line = new_text
                self._last_validation_state = False
                return CommandRenderResultDTO(lines=[new_text], color=COLOR.FAILED)

            if self._active_line:
                self._undo_stack.append(self._active_line)
                self._active_line = self._active_line[:-1]

            self._last_validation_state = False
            return CommandRenderResultDTO(lines=[self._active_line], color=COLOR.FAILED)

    def on_enter(self) -> CommandRenderResultDTO:
        try:
            result = self._controller.on_confirm(self._last_validation_state)
            if result is None:
                self._append_limited(self._log, CommandLogEntryDTO(input=self.active_line, success=True, message="Invalid expression.", result=result), Limit.MAX_LOG)
                return CommandRenderResultDTO(
                    lines=[self._active_line],
                    color=COLOR.INCOMPLETE)
            formatted = self._formatter.format_decimal(result)
            self._last_result_formatted = formatted
            entry = CommandEntryDTO(
                input=self._active_line,
                output=formatted)
            self._last_result_raw = result
            self._append_limited(self._history, entry, Limit.MAX_HISTORY)
            self._append_limited(self._log, CommandLogEntryDTO(input=self.active_line, success=True, message=None, result=self._last_result_raw), Limit.MAX_LOG)
            self._active_line = ""
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._last_validation_state = False
            return CommandRenderResultDTO(lines=[formatted, ""], color=COLOR.SUCCESS)
        except Exception as e:
            self._append_limited(self._log, CommandLogEntryDTO(input=self.active_line, success=True, message=None, result=self._last_result_raw), Limit.MAX_LOG)
            return CommandRenderResultDTO(
                lines=[self._active_line, str(e)],
                color=COLOR.FAILED)

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._active_line)
        self._active_line = self._undo_stack.pop()

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._active_line)
        self._active_line = self._redo_stack.pop()

    def delete(self) -> None:
        if self._active_line:
            self._undo_stack.append(self._active_line)
            self._redo_stack.clear()
            self._active_line = self._active_line[:-1]
            return

        if self._history:
            self._undo_stack.append("")
            self._redo_stack.clear()
            last_entry = self._history.pop()
            self._active_line = last_entry.input

    def copy_formatted(self) -> Optional[str]:
        return self._last_result_formatted

    def copy_raw(self) -> Optional[str]:
        if self._last_result_raw is None:
            return None
        return self._clean_formatter.format(self._last_result_raw)

    def _append_log(
            self,
            input_text: str,
            success: bool,
            message: Optional[str] = None,
            result: Optional[Number] = None) -> None:
        self._log.append(
            CommandLogEntryDTO(
                input=input_text,
                success=success,
                message=message,
                result=result))

    def _append_limited(self, target: list, value, max_size: int) -> None:
        target.append(value)
        if len(target) > max_size:
            target.pop(0)