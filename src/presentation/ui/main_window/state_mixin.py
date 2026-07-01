from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker, QSize

from src.modules.application_dtos import (
    ApplicationContextDTO,
    NumericWorkbenchPreferencesDTO,
    ProgramContextDTO,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchPreferencesDTO, BinaryWorkbenchStateDTO
from src.modules.converter_dtos import ConverterStateDTO
from src.modules.shared_dtos import WindowSizeDTO
from src.modules.utils import COLOR
from src.presentation.ui.components.command_panel.constants import COMMAND_PANEL_TEXT
from src.presentation.ui.helpers.window_geometry import ensure_window_on_available_screen
from src.presentation.ui.main_window.constants import MAIN_WINDOW_STATE, MAIN_WINDOW_TEXT

if TYPE_CHECKING:
    from src.presentation.ui.main_window.window import MainWindow


class MainWindowStateMixin:
    def _load_default_state(self: MainWindow) -> None:
        self._program_context = self._state_service.load_program_context()
        self._binary_workbench_state = self._state_service.load_default_binary_context()
        self._binary_workbench_preferences = self._binary_preferences_service.load()
        context = self._state_service.load_default_context()
        self._apply_context(context, self._preferences_service.get_preferences())
        self._refresh_command_completions()
        self.footer.set_status(MAIN_WINDOW_TEXT.DEFAULT_CONTEXT_LOADED)

    def _collect_context(self: MainWindow) -> ApplicationContextDTO:
        return ApplicationContextDTO(
            converter=ConverterStateDTO(
                from_type=self._converter_presenter.current_from_type,
                fields=self._converter_presenter.raw_inputs,
                message=self._converter_presenter.last_error_message,
            ),
            command=self._command_presenter.export_context(),
            window_sizes=self._collect_window_sizes(),
        )

    def _apply_context(
        self: MainWindow,
        context: ApplicationContextDTO,
        preferences: NumericWorkbenchPreferencesDTO | None = None,
    ) -> None:
        preferences = preferences or self._preferences_service.get_preferences()
        self._window_sizes = dict(context.window_sizes)
        self._auto_convert_enabled = preferences.auto_convert_enabled
        self._command_presenter.set_log_preferences(preferences.log_preferences)
        self._command_presenter.load_context(context.command)
        self._refresh_workspace_windows()
        self._sync_binary_workbench_window_state()
        self._syncing_command = True
        with QSignalBlocker(self.body.command_panel.editor):
            self.body.command_panel.set_input_text(context.command.active_line)
        self._syncing_command = False

        source_value = context.converter.fields.get(context.converter.from_type, "")
        if source_value:
            output = self._converter_presenter.on_user_input(context.converter.from_type, source_value)
            if output is not None:
                self._render_converter(output)
        else:
            self._converter_presenter.on_user_input(context.converter.from_type, "")
            self.body.converter_panel.set_values(
                {key: "" for key in ("decimal", "binary", "hexBE", "hexLE")},
                {key: "" for key in ("decimal", "binary", "hexBE", "hexLE")},
            )

        with QSignalBlocker(self.toolbar.toggle_key_panel_action):
            self.toolbar.toggle_key_panel_action.setChecked(preferences.key_panel_visible)
        with QSignalBlocker(self.toolbar.auto_convert_action):
            self.toolbar.auto_convert_action.setChecked(preferences.auto_convert_enabled)
        self.key_panel.setVisible(preferences.key_panel_visible)
        self._update_minimum_height(preferences.key_panel_visible)
        self._restore_window_size(MAIN_WINDOW_STATE.MAIN_WINDOW_KEY, self)
        self.body.command_panel.set_feedback(COMMAND_PANEL_TEXT.IDLE_FEEDBACK, COLOR.INFO)

    def _autosave_state(self: MainWindow) -> None:
        if not self._loaded:
            return
        self._state_service.save_default_context(self._collect_context())
        try:
            self._state_service.save_default_binary_context(self._collect_binary_workbench_state())
        except PermissionError:
            self.footer.set_status(MAIN_WINDOW_TEXT.BINARY_WORKBENCH_AUTOSAVE_BLOCKED)
        self._state_service.save_program_context(self._program_context)
        self._binary_preferences_service.save(self._binary_workbench_preferences)
        self._preferences_service.update_numeric_flags(
            self.key_panel.isVisible(),
            self._auto_convert_enabled,
        )

    def _collect_window_sizes(self: MainWindow) -> dict[str, WindowSizeDTO]:
        window_sizes = dict(self._window_sizes)
        window_sizes[MAIN_WINDOW_STATE.MAIN_WINDOW_KEY] = WindowSizeDTO(
            width=self.width(),
            height=self.height(),
        )
        for key, window in (
            (MAIN_WINDOW_STATE.HELP_WINDOW_KEY, self._help_window),
            (MAIN_WINDOW_STATE.VARIABLES_WINDOW_KEY, self._variables_window),
            (MAIN_WINDOW_STATE.LOGS_WINDOW_KEY, self._logs_window),
        ):
            self._collect_secondary_window_size(key, window, window_sizes)
        return window_sizes

    def _collect_secondary_window_size(
        self: MainWindow,
        key: str,
        window: object,
        window_sizes: dict[str, WindowSizeDTO],
    ) -> None:
        if window is None:
            return
        width = getattr(window, "width", None)
        height = getattr(window, "height", None)
        if callable(width) and callable(height):
            window_sizes[key] = WindowSizeDTO(width=width(), height=height())

    def _remember_window_size(
        self: MainWindow,
        key: str,
        width: int,
        height: int,
    ) -> None:
        if key == MAIN_WINDOW_STATE.BINARY_WORKBENCH_WINDOW_KEY:
            self._binary_workbench_state = BinaryWorkbenchStateDTO(
                **{
                    **self._binary_workbench_state.__dict__,
                    "window_size": WindowSizeDTO(width=width, height=height),
                }
            )
            self._autosave_state()
            return
        self._window_sizes[key] = WindowSizeDTO(width=width, height=height)
        self._autosave_state()

    def _restore_window_size(self: MainWindow, key: str, window: object) -> None:
        size = self._window_sizes.get(key)
        resize = getattr(window, "resize", None)
        if size is not None and callable(resize):
            resize(QSize(size.width, size.height))
        if hasattr(window, "frameGeometry"):
            ensure_window_on_available_screen(window, self)

    def _collect_binary_workbench_state(self: MainWindow) -> BinaryWorkbenchStateDTO:
        if self._binary_workbench_window is not None:
            self._binary_workbench_state = self._binary_workbench_window.export_state()
        return self._binary_workbench_state

    def _remember_binary_workbench_state(self: MainWindow, state: object) -> None:
        if not isinstance(state, BinaryWorkbenchStateDTO):
            return
        self._binary_workbench_state = state
        self._autosave_state()

    def _remember_binary_workbench_preferences(self: MainWindow, preferences: object) -> None:
        if not isinstance(preferences, BinaryWorkbenchPreferencesDTO):
            return
        self._binary_workbench_preferences = preferences
        self._autosave_state()

    def _remember_program_context(self: MainWindow, context: object) -> None:
        if not isinstance(context, ProgramContextDTO):
            return
        self._program_context = context
        self._autosave_state()

    def _sync_binary_workbench_window_state(self: MainWindow) -> None:
        if self._binary_workbench_window is None:
            return
        self._binary_workbench_window.load_state(self._binary_workbench_state)
