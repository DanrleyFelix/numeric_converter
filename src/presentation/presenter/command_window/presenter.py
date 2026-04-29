from __future__ import annotations

from src.application.contracts.cmd_window_contract import ICommandWindowController
from src.application.contracts.preferences_contract import IOutputFormatter
from src.application.dto.application_state import CommandContextDTO
from src.application.dto.command_entry import CommandEntryDTO
from src.application.dto.command_render_result import CommandRenderResultDTO
from src.core.command_window.context import cmd_window_context
from src.core.command_window.expression_inspector import (
    has_trailing_identifier_fragment,
    is_standalone_identifier_fragment,
)
from src.core.command_window.validator.errors import UnknownVariableError, ValidationError
from src.presentation.presenter.command_window.editing import trim_invalid_suffix
from src.presentation.presenter.command_window.rendering import (
    render_invalid_expression,
    render_invalid_input,
    render_live_feedback,
    render_submission_failure,
    render_submission_success,
    render_unknown_variable,
)
from src.presentation.presenter.command_window.state import CommandWindowState
from src.presentation.presenter.command_window.workspace_rows import (
    build_workspace_log_rows,
    build_workspace_variable_detail_rows,
)


class CommandWindowPresenter:
    def __init__(
        self,
        controller: ICommandWindowController,
        formatter: IOutputFormatter,
    ):
        self._controller = controller
        self._formatter = formatter
        self._state = CommandWindowState()

    @property
    def history(self) -> list[CommandEntryDTO]:
        return list(self._state.history)

    @property
    def active_line(self) -> str:
        return self._state.active_line

    @property
    def variable_names(self) -> list[str]:
        return sorted(cmd_window_context.get_variables().keys())

    @property
    def workspace_variable_detail_rows(self) -> list[tuple[str, str, str]]:
        return build_workspace_variable_detail_rows(
            cmd_window_context.get_history(),
            cmd_window_context.get_variables(),
        )

    @property
    def workspace_log_rows(self) -> list[tuple[int, str, str]]:
        return build_workspace_log_rows(self._state.history)

    def on_text_changed(
        self,
        new_text: str,
        pasted: bool = False,
    ) -> CommandRenderResultDTO:
        sanitized = new_text.replace("\r", " ").replace("\n", " ")

        self._state.track_line_change(sanitized)

        try:
            validation_state = self._controller.on_input_changed(sanitized)
            self._state.store_live_line(sanitized, validation_state)
            return render_live_feedback(sanitized, validation_state)
        except UnknownVariableError as error:
            return self._render_unknown_variable(sanitized, error)
        except ValidationError as error:
            return self._render_invalid_input(sanitized, pasted, str(error))
        except Exception as error:
            return self._render_invalid_input(sanitized, pasted, str(error))

    def on_enter(self) -> CommandRenderResultDTO:
        try:
            result = self._controller.on_confirm()
            if result is None:
                return render_invalid_expression(self._state.active_line)

            formatted = self._formatter.format_decimal(result)
            cmd_window_context.add_to_history(self._state.active_line)
            self._state.store_submission(formatted, result)
            self._state.reset_after_submission()
            return render_submission_success(formatted)
        except Exception as error:
            return render_submission_failure(self._state.active_line, str(error))

    def delete(self, target: str | None = None) -> None:
        if self._state.delete_active_character():
            return

        if target == "history" and self._state.history:
            self._state.history.pop()
            instructions = cmd_window_context.get_history()
            if instructions:
                cmd_window_context.remove_history_line(len(instructions) - 1)

    def remove_log(self, index: int) -> None:
        if 0 <= index < len(self._state.history):
            self._state.history.pop(index)
        cmd_window_context.remove_history_line(index)

    def remove_variable(self, name: str) -> None:
        cmd_window_context.remove_variable(name)

    def copy_formatted(self) -> str | None:
        return self._state.last_result_formatted

    def copy_raw(self) -> str | None:
        return None if self._state.last_result_raw is None else str(self._state.last_result_raw)

    def export_context(self) -> CommandContextDTO:
        return self._state.export_context(
            instructions=cmd_window_context.get_history(),
            variables=cmd_window_context.get_variables(),
        )

    def load_context(self, context: CommandContextDTO) -> None:
        self._state.load_context(context)
        cmd_window_context.restore(context.variables, context.instructions)

    def _render_unknown_variable(
        self,
        sanitized: str,
        error: UnknownVariableError,
    ) -> CommandRenderResultDTO:
        self._state.active_line = sanitized
        self._state.last_validation_state = False
        is_incomplete = (
            is_standalone_identifier_fragment(sanitized)
            or has_trailing_identifier_fragment(sanitized, error.position)
        )
        return render_unknown_variable(sanitized, is_incomplete, str(error))

    def _render_invalid_input(
        self,
        sanitized: str,
        pasted: bool,
        message: str,
    ) -> CommandRenderResultDTO:
        corrected = trim_invalid_suffix(sanitized, self._controller.on_input_changed)
        self._state.active_line = corrected
        self._state.last_validation_state = False
        return render_invalid_input(corrected, sanitized, pasted, message)
