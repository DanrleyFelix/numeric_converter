from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Number

from src.application.dto.application_state import CommandContextDTO
from src.application.dto.command_entry import CommandEntryDTO
from src.presentation.presenter.command_window.constants import (
    COMMAND_WINDOW_LIMITS,
    COMMAND_WINDOW_VIEW_MODE,
)
from src.presentation.presenter.command_window.editing import append_limited


@dataclass
class CommandWindowState:
    history: list[CommandEntryDTO] = field(default_factory=list)
    active_line: str = ""
    undo_stack: list[str] = field(default_factory=list)
    redo_stack: list[str] = field(default_factory=list)
    last_validation_state: bool = False
    last_result_raw: Number | None = None
    last_result_formatted: str | None = None
    workspace_view_mode: str = COMMAND_WINDOW_VIEW_MODE.VARIABLES

    def reset_after_submission(self) -> None:
        self.active_line = ""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.last_validation_state = False

    def reset_runtime_state(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.last_validation_state = False
        self.last_result_raw = None
        self.last_result_formatted = None

    def track_line_change(self, sanitized: str) -> None:
        if sanitized != self.active_line:
            self.undo_stack.append(self.active_line)
            self.redo_stack.clear()

    def store_live_line(self, sanitized: str, validation_state: bool) -> None:
        self.active_line = sanitized
        self.last_validation_state = validation_state

    def store_submission(self, formatted: str, raw_result: Number) -> None:
        self.last_result_formatted = formatted
        self.last_result_raw = raw_result
        append_limited(
            self.history,
            CommandEntryDTO(input=self.active_line, output=formatted),
            COMMAND_WINDOW_LIMITS.HISTORY_MAX_SIZE,
        )

    def delete_active_character(self) -> bool:
        if not self.active_line:
            return False
        self.undo_stack.append(self.active_line)
        self.redo_stack.clear()
        self.active_line = self.active_line[:-1]
        return True

    def set_workspace_view_mode(self, mode: str) -> None:
        self.workspace_view_mode = (
            COMMAND_WINDOW_VIEW_MODE.LOG
            if mode == COMMAND_WINDOW_VIEW_MODE.LOG
            else COMMAND_WINDOW_VIEW_MODE.VARIABLES
        )

    def export_context(
        self,
        instructions: list[str],
        variables: dict[str, int],
    ) -> CommandContextDTO:
        return CommandContextDTO(
            active_line=self.active_line,
            history=list(self.history),
            instructions=instructions,
            variables=variables,
            workspace_view_mode=self.workspace_view_mode,
        )

    def load_context(self, context: CommandContextDTO) -> None:
        self.active_line = context.active_line
        self.history = list(context.history)
        self.reset_runtime_state()
        self.set_workspace_view_mode(context.workspace_view_mode)
