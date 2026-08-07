from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.list_view import (
    EncodingTablesList,
)
from src.presentation.ui.helpers.load_qss import STYLESHEET


class BinaryWorkbenchRecoveryDialog(QDialog):
    """Let the user bypass an expensive persisted startup tab."""

    def __init__(
        self,
        tabs: list[BinaryWorkbenchTabContextDTO],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._tabs = tabs
        self._excluded: set[str] | None = None
        self._items = {}
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.RECOVERY_TITLE)
        self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.CONTENT_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.ROW_SPACING)
        self.blank_option = self._choice(BINARY_WORKBENCH_TEXT.RECOVERY_BLANK_PROJECT)
        self.recover_option = self._choice(BINARY_WORKBENCH_TEXT.RECOVERY_ALL_TABS)
        self._choice_group = QButtonGroup(self)
        self._choice_group.setExclusive(True)
        self._choice_group.addButton(self.blank_option)
        self._choice_group.addButton(self.recover_option)
        self.blank_option.setChecked(True)
        layout.addWidget(self.blank_option)
        layout.addWidget(self.recover_option)
        self.tabs_list = self._tab_list()
        self.tabs_list.setEnabled(False)
        self.recover_option.toggled.connect(self.tabs_list.setEnabled)
        self.blank_option.toggled.connect(self._clear_exclusions_for_blank)
        layout.addWidget(self.tabs_list, 1)
        confirm = QPushButton(BINARY_WORKBENCH_TEXT.CONFIRM, self)
        configure_binary_workbench_dialog_action(confirm)
        confirm.setFixedWidth(BINARY_WORKBENCH_LAYOUT.RECOVERY_ACTION_WIDTH)
        confirm.clicked.connect(self._confirm_recovery)
        layout.addWidget(confirm, 0, Qt.AlignCenter)
        self.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.RECOVERY_DIALOG_WIDTH,
            BINARY_WORKBENCH_LAYOUT.RECOVERY_DIALOG_HEIGHT,
        )

    def excluded_tab_ids(self) -> set[str] | None:
        """Return selected exclusions, all ids for blank, or None after cancel."""

        return None if self._excluded is None else set(self._excluded)

    def preserves_excluded_tabs(self) -> bool:
        """Return whether unchecked recovery tabs remain persisted for later."""

        return self.recover_option.isChecked()

    def _tab_list(self) -> EncodingTablesList:
        """Create one virtualized project-standard list for tab exclusions."""

        tabs_list = EncodingTablesList(self)
        tabs_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for tab in self._tabs:
            item = tabs_list.append_table(tab.display_name, False)
            item.setData(Qt.ItemDataRole.UserRole, tab.tab_id)
            item.setToolTip(tab.display_name)
            self._items[tab.tab_id] = item
        return tabs_list

    def _clear_exclusions_for_blank(self, checked: bool) -> None:
        """Clear stale exception highlights when Blank project becomes active."""

        if checked:
            self.tabs_list.clearSelection()
            self.tabs_list.setCurrentItem(None)

    def _choice(self, text: str) -> QRadioButton:
        """Create one project-styled, mutually exclusive recovery choice."""

        choice = QRadioButton(text, self)
        choice.setObjectName("binary-workbench-recovery-choice")
        choice.setCursor(Qt.PointingHandCursor)
        return choice

    def _confirm_recovery(self) -> None:
        if self.blank_option.isChecked():
            self._excluded = {tab.tab_id for tab in self._tabs}
        else:
            self._excluded = {
                str(item.data(Qt.ItemDataRole.UserRole))
                for item in self.tabs_list.selectedItems()
            }
        self.accept()
