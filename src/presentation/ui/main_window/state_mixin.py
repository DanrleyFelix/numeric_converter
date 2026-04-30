from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker
from PySide6.QtCore import QSize

from src.application.dto import ApplicationContextDTO, ConverterStateDTO, WindowSizeDTO
from src.modules.utils import COLOR
from src.presentation.ui.components.command_panel.constants import COMMAND_PANEL_TEXT
from src.presentation.ui.main_window.constants import MAIN_WINDOW_STATE, MAIN_WINDOW_TEXT

if TYPE_CHECKING:
    from src.presentation.ui.main_window.window import MainWindow


class MainWindowStateMixin:

    def _load_default_state(self: MainWindow) -> None:
        context = self._state_service.load_default_context()
        self._apply_context(context)
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
            key_panel_visible=self.key_panel.isVisible(),
            auto_convert_enabled=self._auto_convert_enabled,
            window_sizes=self._collect_window_sizes(),
        )

    def _apply_context(self: MainWindow, context: ApplicationContextDTO) -> None:
        self._window_sizes = dict(context.window_sizes)
        self._auto_convert_enabled = context.auto_convert_enabled
        self._command_presenter.load_context(context.command)
        self._refresh_workspace_windows()

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
            self.toolbar.toggle_key_panel_action.setChecked(context.key_panel_visible)
        with QSignalBlocker(self.toolbar.auto_convert_action):
            self.toolbar.auto_convert_action.setChecked(context.auto_convert_enabled)
        self.key_panel.setVisible(context.key_panel_visible)
        self._update_minimum_height(context.key_panel_visible)
        self._restore_window_size(MAIN_WINDOW_STATE.MAIN_WINDOW_KEY, self)
        self.body.command_panel.set_feedback(COMMAND_PANEL_TEXT.IDLE_FEEDBACK, COLOR.INFO)

    def _autosave_state(self: MainWindow) -> None:
        if not self._loaded:
            return
        self._state_service.save_default_context(self._collect_context())

    def _collect_window_sizes(self: MainWindow) -> dict[str, WindowSizeDTO]:
        window_sizes = dict(self._window_sizes)
        window_sizes[MAIN_WINDOW_STATE.MAIN_WINDOW_KEY] = WindowSizeDTO(
            width=self.width(),
            height=self.height(),
        )
        self._collect_secondary_window_size(
            MAIN_WINDOW_STATE.HELP_WINDOW_KEY,
            self._help_window,
            window_sizes,
        )
        self._collect_secondary_window_size(
            MAIN_WINDOW_STATE.VARIABLES_WINDOW_KEY,
            self._variables_window,
            window_sizes,
        )
        self._collect_secondary_window_size(
            MAIN_WINDOW_STATE.LOGS_WINDOW_KEY,
            self._logs_window,
            window_sizes,
        )
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
        self._window_sizes[key] = WindowSizeDTO(width=width, height=height)
        self._autosave_state()

    def _restore_window_size(self: MainWindow, key: str, window: object) -> None:
        size = self._window_sizes.get(key)
        if size is None:
            return
        resize = getattr(window, "resize", None)
        if callable(resize):
            resize(QSize(size.width, size.height))
