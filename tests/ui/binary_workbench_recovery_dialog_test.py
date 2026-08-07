import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QRadioButton, QScrollArea

from src.main import create_main_window
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.presentation.ui.main_window import dialogs_mixin as dialogs_mixin_module
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.list_view import EncodingTablesList
from src.presentation.ui.components.binary_workbench.file_dialogs.recovery_dialog import (
    BinaryWorkbenchRecoveryDialog,
)


def _app() -> QApplication:
    """Return the shared offscreen Qt application."""

    return QApplication.instance() or QApplication([])


def _tabs() -> list[BinaryWorkbenchTabContextDTO]:
    return [
        BinaryWorkbenchTabContextDTO("first", "scratch", "Small project"),
        BinaryWorkbenchTabContextDTO(
            "heavy",
            "scratch",
            "A very long project name that must remain readable in recovery",
        ),
    ]


def test_recovery_dialog_uses_dark_project_list_and_spacing():
    """Protect the startup fallback from reverting to native white controls."""

    _app()
    dialog = BinaryWorkbenchRecoveryDialog(_tabs())
    dialog.show()
    _app().processEvents()
    margins = dialog.layout().contentsMargins()
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    choices = {button.text(): button for button in dialog.findChildren(QRadioButton)}

    assert dialog.objectName() == "preferences-dialog"
    assert dialog.styleSheet()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (
        20,
        20,
        20,
        20,
    )
    assert dialog.layout().spacing() == 15
    assert isinstance(dialog.tabs_list, EncodingTablesList)
    assert dialog.findChildren(QScrollArea) == []
    assert len(choices) == 2
    assert choices[BINARY_WORKBENCH_TEXT.RECOVERY_BLANK_PROJECT].isChecked()
    assert not dialog.tabs_list.isEnabled()
    assert dialog.tabs_list.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert dialog.width() == BINARY_WORKBENCH_LAYOUT.RECOVERY_DIALOG_WIDTH
    assert buttons[BINARY_WORKBENCH_TEXT.CONFIRM].width() == BINARY_WORKBENCH_LAYOUT.RECOVERY_ACTION_WIDTH
    assert dialog.findChildren(QLabel) == []
    dialog.close()


def test_recovery_dialog_excludes_selected_tabs_by_stable_id():
    """Map the virtualized list selection to tab IDs, not visible names."""

    _app()
    dialog = BinaryWorkbenchRecoveryDialog(_tabs())
    dialog.recover_option.setChecked(True)
    dialog.tabs_list.item(1).setSelected(True)

    dialog._confirm_recovery()

    assert dialog.excluded_tab_ids() == {"heavy"}


def test_recovery_dialog_recovers_every_tab_when_no_exception_is_selected():
    """An empty exclusion list means recover every persisted tab."""

    _app()
    dialog = BinaryWorkbenchRecoveryDialog(_tabs())
    dialog.recover_option.setChecked(True)

    dialog._confirm_recovery()

    assert dialog.excluded_tab_ids() == set()


def test_blank_project_clears_exception_selection_and_does_not_preserve_tabs():
    """Blank means a new persisted state, not hidden recovery payloads."""

    _app()
    dialog = BinaryWorkbenchRecoveryDialog(_tabs())
    dialog.recover_option.setChecked(True)
    dialog.tabs_list.item(1).setSelected(True)

    dialog.blank_option.setChecked(True)

    assert dialog.tabs_list.selectedItems() == []
    assert dialog.preserves_excluded_tabs() is False


def test_blank_recovery_immediately_replaces_the_persisted_heavy_state(
    tmp_path,
    monkeypatch,
):
    """Persist Blank even when an empty window cannot emit stateChanged."""

    _app()
    window = create_main_window(tmp_path)
    heavy = BinaryWorkbenchTabContextDTO("heavy", "scratch", "heavy.asm")
    window._binary_workbench_state = BinaryWorkbenchStateDTO(
        tabs=[heavy],
        active_tab_id="heavy",
    )
    window._binary_state_loaded = True

    class _BlankRecovery:
        DialogCode = QDialog.DialogCode

        def __init__(self, *_args, **_kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def excluded_tab_ids(self):
            return {"heavy"}

        def preserves_excluded_tabs(self):
            return False

    monkeypatch.setattr(dialogs_mixin_module, "recovery_plan", lambda _state: object())
    monkeypatch.setattr(
        dialogs_mixin_module,
        "BinaryWorkbenchRecoveryDialog",
        _BlankRecovery,
    )

    window._open_binary_workbench()

    persisted = window._state_service.load_default_binary_context()
    assert window._binary_workbench_state.tabs == []
    assert persisted.tabs == []
    window.close()
