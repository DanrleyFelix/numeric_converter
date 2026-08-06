import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton, QScrollArea

from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.list_view import (
    CONFLICT_ROLE,
    EncodingTablesList,
)
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
    dialog = BinaryWorkbenchRecoveryDialog(_tabs(), "heavy")
    dialog.show()
    _app().processEvents()
    margins = dialog.layout().contentsMargins()
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}

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
    assert dialog.findChildren(QCheckBox) == []
    assert dialog.tabs_list.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert buttons[BINARY_WORKBENCH_TEXT.RECOVERY_BLANK_PROJECT].width() == (
        BINARY_WORKBENCH_LAYOUT.RECOVERY_ACTION_WIDTH
    )
    assert buttons[BINARY_WORKBENCH_TEXT.RECOVERY_ALL_TABS].width() == (
        BINARY_WORKBENCH_LAYOUT.RECOVERY_ACTION_WIDTH
    )
    assert dialog.tabs_list.item(1).data(CONFLICT_ROLE) is True
    dialog.close()


def test_recovery_dialog_excludes_selected_tabs_by_stable_id():
    """Map the virtualized list selection to tab IDs, not visible names."""

    _app()
    dialog = BinaryWorkbenchRecoveryDialog(_tabs(), "heavy")
    dialog._show_exceptions()
    dialog.tabs_list.item(1).setSelected(True)

    dialog._confirm_recovery()

    assert dialog.excluded_tab_ids() == {"heavy"}

