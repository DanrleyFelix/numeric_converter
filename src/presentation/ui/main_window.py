from pathlib import Path

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QFileDialog, QMainWindow, QVBoxLayout, QWidget

from src.application.dto import ApplicationContextDTO, ConverterStateDTO
from src.application.services.formating_preferences import FormattingPreferencesService
from src.application.services.workspace_state_service import WorkspaceStateService
from src.modules.utils import COLOR
from src.presentation.presenter.cmd_window_presenter import CommandWindowPresenter
from src.presentation.presenter.converter_presenter import ConverterPresenter
from src.presentation.ui.components import Body, Footer, KeyPanel, Toolbar
from src.presentation.ui.components.help_window import HelpWindow
from src.presentation.ui.components.preferences_dialog import PreferencesDialog
from src.presentation.ui.design.icons import Icons
from src.presentation.ui.helpers.load_qss import STYLESHEET


class MainWindow(QMainWindow):

    def __init__(
        self,
        converter_presenter: ConverterPresenter,
        command_presenter: CommandWindowPresenter,
        state_service: WorkspaceStateService,
        preferences_service: FormattingPreferencesService,
    ):
        super().__init__()
        self._converter_presenter = converter_presenter
        self._command_presenter = command_presenter
        self._state_service = state_service
        self._preferences_service = preferences_service
        self._help_window: HelpWindow | None = None
        self._syncing_converter = False
        self._syncing_command = False
        self._loaded = False

        self.setMinimumSize(670, 640)
        self.setWindowTitle("Numeric WorkBench")
        self.setWindowIcon(Icons.hexadecimal())

        self.toolbar = Toolbar()
        self.body = Body()
        self.key_panel = KeyPanel()
        self.footer = Footer()

        container = QWidget()
        layout_container = QVBoxLayout(container)
        layout_container.setContentsMargins(16, 16, 16, 16)
        layout_container.setSpacing(16)
        layout_container.addWidget(self.body, 1)
        layout_container.addWidget(self.key_panel)
        layout_container.addWidget(self.footer)
        layout_container.addStretch()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(container, 1)
        layout.addStretch()
        central.setObjectName("main-window")

        self.setCentralWidget(central)
        self.setStyleSheet(STYLESHEET)

        self._bind_events()
        self._load_default_state()
        self._loaded = True

    def closeEvent(self, event):
        self._autosave_state()
        super().closeEvent(event)

    def _bind_events(self) -> None:
        self.body.converter_panel.inputEdited.connect(self._on_converter_input)
        self.body.command_panel.editor.textChanged.connect(self._on_command_text_changed)
        self.body.command_panel.editor.submitted.connect(self._on_command_submitted)
        self.key_panel.keyPressed.connect(self._on_key_panel_pressed)

        self.toolbar.save_workspace_action.triggered.connect(self._save_workspace)
        self.toolbar.load_workspace_action.triggered.connect(self._load_workspace)
        self.toolbar.converter_preferences_action.triggered.connect(self._open_preferences)
        self.toolbar.toggle_key_panel_action.toggled.connect(self.key_panel.setVisible)
        self.toolbar.toggle_key_panel_action.toggled.connect(lambda _: self._autosave_state())
        self.toolbar.help_button.clicked.connect(self._open_help)

    def _load_default_state(self) -> None:
        context = self._state_service.load_default_context()
        log = self._state_service.load_default_log()
        self._apply_context(context)
        self._command_presenter.load_log(log)
        self.body.command_panel.render_log(self._command_presenter.log)
        self._refresh_command_completions()
        self.footer.set_status("Default context and log loaded.")

    def _on_converter_input(self, from_type: str, raw_value: str) -> None:
        if self._syncing_converter:
            return

        output = self._converter_presenter.on_user_input(from_type, raw_value)
        if output is None:
            self.footer.set_status(
                self._converter_presenter.last_error_message or "Invalid converter input.",
                COLOR.FAILED,
            )
            return

        self._render_converter(output)
        self.footer.set_status("Converter updated.", COLOR.SUCCESS)
        self._autosave_state()

    def _on_command_text_changed(self) -> None:
        if self._syncing_command:
            return

        text = self.body.command_panel.current_input()
        result = self._command_presenter.on_text_changed(text)

        if self._command_presenter.active_line != text:
            self._syncing_command = True
            with QSignalBlocker(self.body.command_panel.editor):
                self.body.command_panel.set_input_text(self._command_presenter.active_line)
            self._syncing_command = False

        message = result.message
        if message is None:
            message = "Expression ready." if result.color == COLOR.SUCCESS else "Expression incomplete."

        self.body.command_panel.set_feedback(message, result.color)
        self._refresh_command_completions()
        self._autosave_state()

    def _on_command_submitted(self) -> None:
        result = self._command_presenter.on_enter()
        self._syncing_command = True
        with QSignalBlocker(self.body.command_panel.editor):
            self.body.command_panel.set_input_text(self._command_presenter.active_line)
        self._syncing_command = False

        self.body.command_panel.render_history(self._command_presenter.history)
        self.body.command_panel.render_log(self._command_presenter.log)
        self.body.command_panel.set_feedback(
            result.message or "Expression incomplete.",
            result.color,
        )

        if result.color == COLOR.SUCCESS and self.body.command_panel.convert_enabled():
            self._convert_command_result()

        self._refresh_command_completions()
        self._autosave_state()

    def _on_key_panel_pressed(self, key: str) -> None:
        if key == "ENTER":
            self._on_command_submitted()
            return

        if key == "LOG":
            self.body.command_panel.toggle_history_log()
            self.body.command_panel.set_feedback(
                f"{self.body.command_panel.current_tab_name().title()} panel active.",
                COLOR.SUCCESS,
            )
            return

        if key == "CLEAR":
            self._command_presenter.delete(self.body.command_panel.current_tab_name())
            self._syncing_command = True
            with QSignalBlocker(self.body.command_panel.editor):
                self.body.command_panel.set_input_text(self._command_presenter.active_line)
            self._syncing_command = False
            self.body.command_panel.render_history(self._command_presenter.history)
            self.body.command_panel.render_log(self._command_presenter.log)
            self.body.command_panel.set_feedback("Deleted last item.", COLOR.INCOMPLETE)
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

    def _convert_command_result(self) -> None:
        raw_result = self._command_presenter.copy_raw()
        if raw_result is None or not raw_result.isdigit():
            self.footer.set_status(
                "Convert toggle accepts only non-negative integer results.",
                COLOR.INCOMPLETE,
            )
            return

        output = self._converter_presenter.on_user_input("decimal", raw_result)
        if output is None:
            self.footer.set_status(
                self._converter_presenter.last_error_message or "Unable to convert command result.",
                COLOR.FAILED,
            )
            return

        self._render_converter(output)
        self.footer.set_status("Command result sent to converter.", COLOR.SUCCESS)

    def _save_workspace(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Workspace",
            str(self._state_service.workspace_directory / "workspace.json"),
            "JSON Files (*.json)",
        )
        if not path:
            return
        saved_path = self._state_service.save_workspace(
            self._collect_context(),
            self._command_presenter.export_log(),
            Path(path),
        )
        self.footer.set_status(f"Workspace saved to {saved_path.name}.", COLOR.SUCCESS)

    def _load_workspace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Workspace",
            str(self._state_service.workspace_directory),
            "JSON Files (*.json)",
        )
        if not path:
            return
        workspace = self._state_service.load_workspace(Path(path))
        self._apply_context(workspace.context)
        self._command_presenter.load_log(workspace.log)
        self.body.command_panel.render_log(self._command_presenter.log)
        self._refresh_command_completions()
        self.footer.set_status(f"Workspace loaded from {Path(path).name}.", COLOR.SUCCESS)
        self._autosave_state()

    def _open_preferences(self) -> None:
        dialog = PreferencesDialog(
            formatting=self._preferences_service.get_format(),
            key_panel_visible=self.key_panel.isVisible(),
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        formatting = dialog.selected_formatting()
        for key, config in formatting.items():
            self._preferences_service.update(key, config)

        self.key_panel.setVisible(dialog.key_panel_visible())
        self.toolbar.toggle_key_panel_action.setChecked(dialog.key_panel_visible())

        output = self._converter_presenter.update_formatting(formatting)
        if output is not None:
            self._render_converter(output)

        self.footer.set_status("Preferences updated.", COLOR.SUCCESS)
        self._autosave_state()

    def _open_help(self) -> None:
        if self._help_window is None:
            self._help_window = HelpWindow(self)
            self._help_window.destroyed.connect(lambda *_: self._clear_help_window())

        self._help_window.show()
        self._help_window.raise_()
        self._help_window.activateWindow()

    def _clear_help_window(self) -> None:
        self._help_window = None

    def _collect_context(self) -> ApplicationContextDTO:
        return ApplicationContextDTO(
            converter=ConverterStateDTO(
                from_type=self._converter_presenter.current_from_type,
                fields=self._converter_presenter.raw_inputs,
                message=self._converter_presenter.last_error_message,
            ),
            command=self._command_presenter.export_context(),
            key_panel_visible=self.key_panel.isVisible(),
        )

    def _apply_context(self, context: ApplicationContextDTO) -> None:
        self._command_presenter.load_context(context.command)
        self.body.command_panel.render_history(self._command_presenter.history)
        self.body.command_panel.render_log(self._command_presenter.log)

        self._syncing_command = True
        with QSignalBlocker(self.body.command_panel.editor):
            self.body.command_panel.set_input_text(context.command.active_line)
        self._syncing_command = False

        source_value = context.converter.fields.get(context.converter.from_type, "")
        if source_value:
            output = self._converter_presenter.on_user_input(
                context.converter.from_type,
                source_value,
            )
            if output is not None:
                self._render_converter(output)
        else:
            self._converter_presenter.on_user_input(context.converter.from_type, "")
            self.body.converter_panel.set_values(
                {key: "" for key in ("decimal", "binary", "hexBE", "hexLE")},
                {key: "" for key in ("decimal", "binary", "hexBE", "hexLE")},
            )

        self.key_panel.setVisible(context.key_panel_visible)
        self.toolbar.toggle_key_panel_action.setChecked(context.key_panel_visible)
        self.body.command_panel.set_feedback("Type an expression and press Enter.", COLOR.INCOMPLETE)

    def _render_converter(self, display_values: dict[str, str]) -> None:
        self._syncing_converter = True
        self.body.converter_panel.set_values(
            self._converter_presenter.raw_inputs,
            display_values,
        )
        self._syncing_converter = False

    def _refresh_command_completions(self) -> None:
        self.body.command_panel.set_completions(self._command_presenter.variable_names)

    def _map_key_panel_input(self, key: str) -> str:
        if key == "x":
            return "*"
        if key == "/":
            return "/"
        if key in {"NOT", "AND", "OR", "XOR"}:
            active_line = self._command_presenter.active_line
            prefix = "" if not active_line or active_line.endswith((" ", "(")) else " "
            return f"{prefix}{key} "
        return key

    def _autosave_state(self) -> None:
        if not self._loaded:
            return
        self._state_service.save_default_context(self._collect_context())
        self._state_service.save_default_log(self._command_presenter.export_log())
