from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QScrollArea, QVBoxLayout, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchVersionDTO
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
    BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT,
)


class BinaryWorkbenchVersionChangeDialog(QDialog):
    def __init__(
        self,
        versions: list[BinaryWorkbenchVersionDTO],
        active_name: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._selected_name: str | None = None
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_CHANGE_TITLE)
        layout = QVBoxLayout(self)
        layout.addWidget(self._versions_scroll(versions, active_name), 1)

    def selected_name(self) -> str | None:
        return self._selected_name

    def _versions_scroll(
        self,
        versions: list[BinaryWorkbenchVersionDTO],
        active_name: str | None,
    ) -> QScrollArea:
        scroll = QScrollArea(self)
        scroll.setObjectName("binary-workbench-version-scroll")
        scroll.setWidgetResizable(True)
        shell = QWidget(scroll)
        shell.setObjectName("binary-workbench-version-list")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(
            BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.CHANGE_LIST_MARGIN,
            BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.CHANGE_LIST_MARGIN,
            BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.CHANGE_LIST_MARGIN,
            BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.CHANGE_LIST_MARGIN,
        )
        layout.setSpacing(BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.CHANGE_LIST_SPACING)
        for version in versions:
            button = QPushButton(version.name, shell)
            button.setObjectName(
                "binary-workbench-version-active"
                if version.name == active_name
                else "binary-workbench-version-item"
            )
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _, name=version.name: self._choose(name))
            layout.addWidget(button)
        layout.addStretch(1)
        scroll.setWidget(shell)
        return scroll

    def _choose(self, name: str) -> None:
        self._selected_name = name
        self.accept()
