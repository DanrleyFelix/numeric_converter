import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPlainTextEdit, QPushButton, QTextBrowser

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

    assert window.body.command_panel.feedback.text() == "Type an expression..."
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


def test_command_feedback_keeps_typing_identifier_after_logical_operator():
    window = _window()

    window.body.command_panel.set_input_text("20 A")
    window._on_command_text_changed()
    assert window.body.command_panel.current_input() == "20 A"
    assert window.body.command_panel.feedback.text() == "Expression incomplete."
    assert COLOR.INCOMPLETE in window.body.command_panel.feedback.styleSheet()

    window.body.command_panel.set_input_text("20 AN")
    window._on_command_text_changed()
    assert window.body.command_panel.current_input() == "20 AN"
    assert window.body.command_panel.feedback.text() == "Expression incomplete."
    assert COLOR.INCOMPLETE in window.body.command_panel.feedback.styleSheet()

    window.body.command_panel.set_input_text("20 AND")
    window._on_command_text_changed()
    assert window.body.command_panel.current_input() == "20 AND"
    assert window.body.command_panel.feedback.text() == "Expression incomplete."
    assert COLOR.INCOMPLETE in window.body.command_panel.feedback.styleSheet()

    window.body.command_panel.set_input_text("20 AND O")
    window._on_command_text_changed()
    assert window.body.command_panel.current_input() == "20 AND O"
    assert window.body.command_panel.feedback.text() == "Expression incomplete."
    assert COLOR.INCOMPLETE in window.body.command_panel.feedback.styleSheet()

    window.body.command_panel.set_input_text("20 AND orbit")
    window._on_command_text_changed()
    assert window.body.command_panel.current_input() == "20 AND orbit"
    assert window.body.command_panel.feedback.text() == "Expression incomplete."
    assert COLOR.INCOMPLETE in window.body.command_panel.feedback.styleSheet()


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
    assert browser.verticalScrollBar().objectName() == "help-page-scrollbar"


def test_command_panel_shows_workspace_buttons_without_convert_toggle():
    window = _window()

    assert window.body.command_panel.findChild(QLabel, "command-title") is None
    assert window.body.command_panel.findChild(QPlainTextEdit, "command-workspace-view") is None
    assert isinstance(window.body.command_panel.show_variables_button, QPushButton)
    assert isinstance(window.body.command_panel.show_logs_button, QPushButton)
    assert window.body.command_panel.show_variables_button.text() == "Variables"
    assert window.body.command_panel.show_logs_button.text() == "Logs"
    assert not hasattr(window.body.command_panel, "convert_toggle")


def test_main_window_minimum_height_shrinks_when_key_panel_is_hidden():
    window = _window()
    initial_min_width = window.minimumWidth()
    initial_min_height = window.minimumHeight()

    window.toolbar.toggle_key_panel_action.setChecked(False)

    assert window.minimumWidth() < initial_min_width
    assert window.minimumWidth() == 790
    assert window.minimumHeight() < initial_min_height


def test_key_panel_visibility_is_restored_as_hidden_from_saved_context():
    root = Path(tempfile.mkdtemp())
    window = create_main_window(root)
    window.toolbar.toggle_key_panel_action.setChecked(False)
    window.close()

    restored = create_main_window(root)

    assert restored.toolbar.toggle_key_panel_action.isChecked() is False
    assert restored.key_panel.isVisible() is False


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
    assert window._variables_window.row_widgets[0].values == ("alpha", "5", "0x5")
    assert window._logs_window.row_widgets[0].values == ("alpha=5", "5")
    assert window._variables_window.row_widgets[0].remove_button.text() == ""
    assert not window._variables_window.row_widgets[0].remove_button.icon().isNull()
    assert window._logs_window.row_widgets[0].remove_button.text() == ""
    assert not window._logs_window.row_widgets[0].remove_button.icon().isNull()
    assert (
        window._variables_window.row_widgets[0].cell_labels[0].textInteractionFlags()
        & Qt.TextSelectableByMouse
    )
    assert (
        window._variables_window.row_widgets[0].cell_labels[2].textInteractionFlags()
        & Qt.TextSelectableByMouse
    )

    window._variables_window.row_widgets[0].remove_button.click()
    assert "alpha" not in window._command_presenter.variable_names

    window._logs_window.row_widgets[0].remove_button.click()
    assert [entry.input for entry in window._command_presenter.history] == ["alpha+3"]


def test_auto_convert_sends_successful_command_result_to_converter():
    window = _window()
    window._auto_convert_enabled = True

    window.body.command_panel.set_input_text("16+4")
    window._on_command_text_changed()
    window._on_command_submitted()

    assert window.body.converter_panel.inputs["decimal"].raw_value == "20"


def test_preferences_dialog_only_shows_converter_formatting():
    _app()
    window = _window()
    formatting = {
        "decimal": FormattingOutputDTO(group_size=3, zero_pad=False),
        "binary": FormattingOutputDTO(group_size=8, zero_pad=True),
        "hexBE": FormattingOutputDTO(group_size=2, zero_pad=False),
        "hexLE": FormattingOutputDTO(group_size=2, zero_pad=True),
    }
    dialog = PreferencesDialog(formatting=formatting)

    assert dialog.findChild(QLabel, "preferences-title") is not None
    assert dialog.findChild(QLabel, "preferences-subtitle") is not None
    assert dialog.findChild(QLabel, "preferences-section-title") is None
    assert window.toolbar.auto_convert_action.text() == "Auto Convert"
    assert window.toolbar.toggle_key_panel_action.text() == "Show Key Panel"


def test_converter_inputs_keep_copy_buttons_outside_editors_at_minimum_width():
    window = _window()
    window.toolbar.toggle_key_panel_action.setChecked(False)
    window.resize(window.minimumWidth(), window.height())
    window.show()
    _app().processEvents()

    for kind, editor in window.body.converter_panel.inputs.items():
        button = window.body.converter_panel.copy_raw_buttons[kind]
        assert editor.minimumWidth() == 150
        assert editor.geometry().right() < button.geometry().left()


def test_secondary_windows_are_single_instance_and_non_modal():
    window = _window()

    window._open_help()
    window._open_variables_window()
    window._open_logs_window()

    help_window = window._help_window
    variables_window = window._variables_window
    logs_window = window._logs_window

    assert help_window is not None and not help_window.isModal()
    assert variables_window is not None and not variables_window.isModal()
    assert logs_window is not None and not logs_window.isModal()
    assert help_window.styleSheet() != ""
    assert variables_window.styleSheet() != ""
    assert logs_window.styleSheet() != ""

    window._open_help()
    window._open_variables_window()
    window._open_logs_window()

    assert window._help_window is help_window
    assert window._variables_window is variables_window
    assert window._logs_window is logs_window


def test_window_size_and_auto_convert_are_restored_from_saved_context():
    root = Path(tempfile.mkdtemp())
    window = create_main_window(root)
    window.resize(910, 680)
    window._auto_convert_enabled = True

    window._open_help()
    window._open_variables_window()
    window._open_logs_window()

    assert window._help_window is not None
    assert window._variables_window is not None
    assert window._logs_window is not None

    window._help_window.resize(980, 700)
    window._variables_window.resize(760, 530)
    window._logs_window.resize(780, 540)
    window.close()

    restored = create_main_window(root)
    restored._open_help()
    restored._open_variables_window()
    restored._open_logs_window()

    assert restored._auto_convert_enabled is True
    assert restored.size().width() == 980
    assert restored.size().height() == 680
    assert restored._help_window is not None
    assert restored._help_window.size().width() == 980
    assert restored._help_window.size().height() == 700
    assert restored._variables_window is not None
    assert restored._variables_window.size().width() == 760
    assert restored._variables_window.size().height() == 530
    assert restored._logs_window is not None
    assert restored._logs_window.size().width() == 780
    assert restored._logs_window.size().height() == 540
