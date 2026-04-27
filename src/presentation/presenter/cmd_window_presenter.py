from numbers import Number
from typing import List, Optional

from src.application.contracts.cmd_window_contract import ICommandWindowController
from src.application.contracts.preferences_contract import IOutputFormatter
from src.application.dto.application_state import CommandContextDTO
from src.application.dto.command_entry import CommandEntryDTO
from src.application.dto.command_render_result import CommandRenderResultDTO
from src.core.command_window.context import cmd_window_context
from src.core.command_window.tokenizer import Tokenizer, TokenType
from src.core.command_window.validator.errors import UnknownVariableError, ValidationError
from src.modules.utils import COLOR
from src.presentation.presenter.utils import Limit


class CommandWindowPresenter:

    def __init__(
        self,
        controller: ICommandWindowController,
        formatter: IOutputFormatter,
    ):

        self._controller = controller
        self._formatter = formatter

        self._history: List[CommandEntryDTO] = []
        self._active_line: str = ""

        self._undo_stack: List[str] = []
        self._redo_stack: List[str] = []

        self._last_validation_state: bool = False
        self._last_result_raw: Optional[Number] = None
        self._last_result_formatted: Optional[str] = None
        self._workspace_view_mode: str = "variables"

    @property
    def history(self) -> List[CommandEntryDTO]:
        return list(self._history)

    @property
    def active_line(self) -> str:
        return self._active_line

    @property
    def variable_names(self) -> list[str]:
        return sorted(cmd_window_context.get_variables().keys())

    @property
    def workspace_variables(self) -> list[str]:
        return [f"{name} = {value}" for name, value in self.workspace_variable_rows]

    @property
    def workspace_variable_rows(self) -> list[tuple[str, str]]:
        instructions = cmd_window_context.get_history()
        variables = cmd_window_context.get_variables()

        ordered_names: list[str] = []
        for instruction in instructions:
            name = self._assignment_name(instruction)
            if not name or name == "ANS" or name not in variables:
                continue
            if name in ordered_names:
                ordered_names.remove(name)
            ordered_names.append(name)

        for name in variables:
            if name == "ANS" or name in ordered_names:
                continue
            ordered_names.append(name)

        return [(name, str(variables[name])) for name in ordered_names]

    @property
    def workspace_log_rows(self) -> list[tuple[int, str, str]]:
        return [
            (index, entry.input, entry.output or "")
            for index, entry in enumerate(self._history)
        ]

    @property
    def workspace_view_mode(self) -> str:
        return self._workspace_view_mode

    def set_workspace_view_mode(self, mode: str) -> None:
        self._workspace_view_mode = "log" if mode == "log" else "variables"

    def on_text_changed(self, new_text: str, pasted: bool = False) -> CommandRenderResultDTO:
        sanitized = new_text.replace("\r", " ").replace("\n", " ")

        if sanitized != self._active_line:
            self._undo_stack.append(self._active_line)
            self._redo_stack.clear()

        try:
            validation_state = self._controller.on_input_changed(sanitized)
            self._active_line = sanitized
            self._last_validation_state = validation_state
            color = COLOR.SUCCESS if validation_state else COLOR.INCOMPLETE
            return CommandRenderResultDTO(lines=[sanitized], color=color)
        except UnknownVariableError as error:
            self._active_line = sanitized
            self._last_validation_state = False
            if self._is_standalone_identifier_fragment(sanitized):
                return CommandRenderResultDTO(
                    lines=[sanitized],
                    color=COLOR.INCOMPLETE,
                )
            return CommandRenderResultDTO(
                lines=[sanitized],
                color=COLOR.FAILED,
                message=str(error),
            )
        except ValidationError as error:
            corrected = self._trim_invalid_suffix(sanitized)
            self._active_line = corrected
            self._last_validation_state = False
            return CommandRenderResultDTO(
                lines=[corrected],
                color=COLOR.INCOMPLETE,
                message=None if corrected != sanitized or pasted else str(error),
            )
        except Exception as error:
            corrected = self._trim_invalid_suffix(sanitized)
            self._active_line = corrected
            self._last_validation_state = False
            return CommandRenderResultDTO(
                lines=[corrected],
                color=COLOR.INCOMPLETE,
                message=None if corrected != sanitized or pasted else str(error),
            )

    def on_enter(self) -> CommandRenderResultDTO:
        try:
            result = self._controller.on_confirm()
            if result is None:
                return CommandRenderResultDTO(
                    lines=[self._active_line],
                    color=COLOR.FAILED,
                    message="Invalid expression.",
                )

            formatted = self._formatter.format_decimal(result)
            self._last_result_formatted = formatted
            self._last_result_raw = result
            cmd_window_context.add_to_history(self._active_line)
            self._append_limited(
                self._history,
                CommandEntryDTO(input=self._active_line, output=formatted),
                Limit.MAX_HISTORY,
            )
            self._active_line = ""
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._last_validation_state = False
            return CommandRenderResultDTO(
                lines=[formatted, ""],
                color=COLOR.SUCCESS,
                message=formatted,
            )
        except Exception as error:
            return CommandRenderResultDTO(
                lines=[self._active_line, str(error)],
                color=COLOR.FAILED,
                message=str(error),
            )

    def delete(self, target: str | None = None) -> None:
        if self._active_line:
            self._undo_stack.append(self._active_line)
            self._redo_stack.clear()
            self._active_line = self._active_line[:-1]
            return

        if target == "history":
            if self._history:
                self._history.pop()
            instructions = cmd_window_context.get_history()
            if instructions:
                cmd_window_context.remove_history_line(len(instructions) - 1)
            return

    def remove_log(self, index: int) -> None:
        if 0 <= index < len(self._history):
            self._history.pop(index)
        cmd_window_context.remove_history_line(index)

    def remove_variable(self, name: str) -> None:
        cmd_window_context.remove_variable(name)

    def copy_formatted(self) -> Optional[str]:
        return self._last_result_formatted

    def copy_raw(self) -> Optional[str]:
        if self._last_result_raw is None:
            return None
        return str(self._last_result_raw)

    def export_context(self) -> CommandContextDTO:
        return CommandContextDTO(
            active_line=self._active_line,
            history=list(self._history),
            instructions=cmd_window_context.get_history(),
            variables=cmd_window_context.get_variables(),
            workspace_view_mode=self._workspace_view_mode,
        )

    def load_context(self, context: CommandContextDTO) -> None:
        self._active_line = context.active_line
        self._history = list(context.history)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._last_validation_state = False
        self._last_result_raw = None
        self._last_result_formatted = None
        self._workspace_view_mode = "log" if context.workspace_view_mode == "log" else "variables"
        cmd_window_context.restore(context.variables, context.instructions)

    def _trim_invalid_suffix(self, text: str) -> str:
        candidate = text
        while candidate:
            candidate = candidate[:-1]
            try:
                self._controller.on_input_changed(candidate)
                return candidate
            except UnknownVariableError:
                return candidate
            except Exception:
                continue
        return ""

    def _append_limited(self, target: list, value, max_size: int) -> None:
        target.append(value)
        if len(target) > max_size:
            target.pop(0)

    def _is_standalone_identifier_fragment(self, text: str) -> bool:
        try:
            tokens = [
                token
                for token in Tokenizer(text).tokenize()
                if token.type != TokenType.EOF
            ]
        except Exception:
            return False
        return len(tokens) == 1 and tokens[0].type == TokenType.IDENTIFIER

    def _assignment_name(self, text: str) -> str | None:
        try:
            tokens = [
                token
                for token in Tokenizer(text).tokenize()
                if token.type != TokenType.EOF
            ]
        except Exception:
            return None
        if (
            len(tokens) >= 3
            and tokens[0].type == TokenType.IDENTIFIER
            and tokens[1].type == TokenType.OPERATOR
            and tokens[1].raw == "="
        ):
            return str(tokens[0].raw)
        return None
