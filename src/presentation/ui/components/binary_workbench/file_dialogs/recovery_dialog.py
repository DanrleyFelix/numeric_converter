from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

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
        suspected_tab_id: str,
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
        explanation = QLabel(BINARY_WORKBENCH_TEXT.RECOVERY_EXPLANATION, self)
        explanation.setWordWrap(True)
        explanation.setObjectName("preferences-subtitle")
        layout.addWidget(explanation)
        choices = QHBoxLayout()
        choices.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.EMPTY_MARGINS)
        choices.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.ROW_SPACING)
        blank = QPushButton(BINARY_WORKBENCH_TEXT.RECOVERY_BLANK_PROJECT, self)
        configure_binary_workbench_dialog_action(blank)
        blank.setFixedWidth(BINARY_WORKBENCH_LAYOUT.RECOVERY_ACTION_WIDTH)
        blank.clicked.connect(self._choose_blank)
        choices.addStretch(1)
        choices.addWidget(blank)
        recover = QPushButton(BINARY_WORKBENCH_TEXT.RECOVERY_ALL_TABS, self)
        configure_binary_workbench_dialog_action(recover)
        recover.setFixedWidth(BINARY_WORKBENCH_LAYOUT.RECOVERY_ACTION_WIDTH)
        recover.clicked.connect(self._show_exceptions)
        choices.addWidget(recover)
        choices.addStretch(1)
        layout.addLayout(choices)
        self._exceptions = QWidget(self)
        exception_layout = QVBoxLayout(self._exceptions)
        exception_layout.setContentsMargins(0, 0, 0, 0)
        exception_layout.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.ROW_SPACING)
        exception_layout.addWidget(QLabel(BINARY_WORKBENCH_TEXT.RECOVERY_EXCEPT, self._exceptions))
        self.tabs_list = self._tab_list(suspected_tab_id)
        exception_layout.addWidget(self.tabs_list, 1)
        confirm = QPushButton(BINARY_WORKBENCH_TEXT.CONFIRM, self._exceptions)
        configure_binary_workbench_dialog_action(confirm)
        confirm.clicked.connect(self._confirm_recovery)
        exception_layout.addWidget(confirm, 0, Qt.AlignCenter)
        self._exceptions.hide()
        layout.addWidget(self._exceptions, 1)
        self.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.RECOVERY_DIALOG_WIDTH,
            BINARY_WORKBENCH_LAYOUT.RECOVERY_DIALOG_HEIGHT,
        )

    def excluded_tab_ids(self) -> set[str] | None:
        """Return selected exclusions, all ids for blank, or None after cancel."""

        return None if self._excluded is None else set(self._excluded)

    def _tab_list(self, suspected_tab_id: str) -> EncodingTablesList:
        """Create one virtualized project-standard list for tab exclusions."""

        tabs_list = EncodingTablesList(self._exceptions)
        tabs_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for tab in self._tabs:
            item = tabs_list.append_table(tab.display_name, False)
            item.setData(Qt.ItemDataRole.UserRole, tab.tab_id)
            item.setToolTip(tab.display_name)
            tabs_list.set_conflict(item, tab.tab_id == suspected_tab_id)
            self._items[tab.tab_id] = item
        return tabs_list

    def _choose_blank(self) -> None:
        self._excluded = {tab.tab_id for tab in self._tabs}
        self.accept()

    def _show_exceptions(self) -> None:
        self._exceptions.show()

    def _confirm_recovery(self) -> None:
        self._excluded = {
            str(item.data(Qt.ItemDataRole.UserRole))
            for item in self.tabs_list.selectedItems()
        }
        self.accept()
