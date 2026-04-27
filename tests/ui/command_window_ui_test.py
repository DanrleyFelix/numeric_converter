import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QPlainTextEdit, QPushButton, QTextBrowser

from src.application.dto.formatting_context import FormattingOutputDTO
from src.main import create_main_window
from src.modules.utils import COLOR
from src.presentation.ui.components.preferences_dialog import PreferencesDialog


_APP = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _window():
    _app()
    return create_main_window(Path(tempfile.mkdtemp()))


def test_command_feedback_uses_blue_idle_yellow_incomplete_and_red_on_enter():
    window = _window()

    assert window.body.command_panel.feedback.text() == "Type an expression and press Enter."
    assert COLOR.INFO in window.body.command_panel.feedback.styleSheet()

    window.body.command_panel.set_input_text("NOT1")
    window._on_command_text_changed()
    assert window.body.command_panel.feedback.text() == "Expression incomplete."
    assert COLOR.INCOMPLETE in window.body.command_panel.feedback.styleSheet()

    window._on_command_submitted()
    assert window.body.command_panel.feedback.text() == "Invalid expression."
    assert COLOR.FAILED in window.body.command_panel.feedback.styleSheet()


def test_command_feedback_reports_unknown_variable_for_complete_expression():
    window = _window()

    window.body.command_panel.set_input_text("(A AND B)OR(B XOR 1)")
    window._on_command_text_changed()

    assert window.body.command_panel.feedback.text() == 'Unknown variable "A".'
    assert COLOR.FAILED in window.body.command_panel.feedback.styleSheet()


def test_key_panel_textual_buttons_add_trailing_space():
    window = _window()

    window._on_key_panel_pressed("NOT")
    assert window.body.command_panel.current_input() == "NOT "

    window.body.command_panel.set_input_text("A")
    window._on_command_text_changed()
    window._on_key_panel_pressed("AND")
    assert window.body.command_panel.current_input() == "A AND "


def test_toolbar_action_has_no_icon_and_help_title_is_user_guide():
    window = _window()

    assert window.toolbar.toggle_key_panel_action.icon().isNull()
    window.toolbar.toggle_key_panel_action.setChecked(False)
    assert window.toolbar.toggle_key_panel_action.icon().isNull()

    window._open_help()
    title = window._help_window.findChild(QLabel, "help-title")
    assert title is not None
    assert title.text() == "User Guide"
    page = window._help_window.pages.currentWidget()
    browser = page.findChild(QTextBrowser, "help-page")
    assert browser is not None
    assert browser.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert browser.verticalScrollBar().styleSheet()


def test_command_panel_shows_workspace_buttons_and_convert_toggle():
    window = _window()

    assert window.body.command_panel.findChild(QLabel, "command-title") is None
    assert window.body.command_panel.findChild(QPlainTextEdit, "command-workspace-view") is None
    assert isinstance(window.body.command_panel.show_variables_button, QPushButton)
    assert isinstance(window.body.command_panel.show_logs_button, QPushButton)
    assert window.body.command_panel.show_variables_button.text() == "Variables"
    assert window.body.command_panel.show_logs_button.text() == "Logs"


def test_workspace_windows_show_rows_and_support_removal():
    window = _window()

    window.body.command_panel.set_input_text("alpha=5")
    window._on_command_text_changed()
    window._on_command_submitted()

    window.body.command_panel.set_input_text("alpha+3")
    window._on_command_text_changed()
    window._on_command_submitted()

    window._open_variables_window()
    window._open_logs_window()

    assert window._variables_window is not None
    assert window._logs_window is not None
    assert len(window._variables_window.row_widgets) == 1
    assert len(window._logs_window.row_widgets) == 2
    assert window._variables_window.row_widgets[0].values == ("alpha", "5")
    assert window._logs_window.row_widgets[0].values == ("alpha=5", "5")
    assert window._variables_window.row_widgets[0].remove_button.text() == "-"
    assert window._logs_window.row_widgets[0].remove_button.text() == "-"

    window._variables_window.row_widgets[0].remove_button.click()
    assert "alpha" not in window._command_presenter.variable_names

    window._logs_window.row_widgets[0].remove_button.click()
    assert [entry.input for entry in window._command_presenter.history] == ["alpha+3"]


def test_preferences_dialog_shows_exclusive_workspace_view_options():
    _app()
    formatting = {
        "decimal": FormattingOutputDTO(group_size=3, zero_pad=False),
        "binary": FormattingOutputDTO(group_size=8, zero_pad=True),
        "hexBE": FormattingOutputDTO(group_size=2, zero_pad=False),
        "hexLE": FormattingOutputDTO(group_size=2, zero_pad=True),
    }
    dialog = PreferencesDialog(formatting=formatting)

    assert dialog.findChild(QLabel, "preferences-title") is not None
    assert dialog.findChild(QLabel, "preferences-subtitle") is not None
    assert dialog.findChild(QCheckBox, "preferences-key-panel") is None
    assert dialog.findChild(QLabel, "preferences-section-title") is None
