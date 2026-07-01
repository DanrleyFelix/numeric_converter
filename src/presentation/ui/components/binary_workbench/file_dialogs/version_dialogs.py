from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout

from src.modules.binary_workbench_dtos import BinaryWorkbenchVersionDTO
from src.presentation.ui.components.binary_workbench.dialog_context_menu import (
    configure_dialog_text_context_menu,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
    BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT,
)


class BinaryWorkbenchVersionNameDialog(QDialog):
    def __init__(self, title: str, initial_value: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.CONTENT_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.ROW_SPACING)
        self.name_field = QLineEdit(initial_value, self)
        configure_dialog_text_context_menu(self.name_field)
        self.name_field.setObjectName("binary-workbench-dialog-input")
        self.name_field.setPlaceholderText(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_NAME_LABEL)
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.CONFIRM, self)
        ok.setObjectName("preferences-confirm")
        ok.setFocusPolicy(Qt.StrongFocus)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        self.name_field.setFixedSize(
            BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.NAME_FIELD_WIDTH,
            BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.NAME_FIELD_HEIGHT,
        )
        ok.setFixedSize(
            BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.NAME_FIELD_WIDTH,
            BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.NAME_FIELD_HEIGHT,
        )
        layout.addWidget(self.name_field, 0, Qt.AlignHCenter)
        layout.addWidget(ok, 0, Qt.AlignHCenter)

    def version_name(self) -> str:
        return self.name_field.text().strip()


class BinaryWorkbenchVersionPickerDialog(QDialog):
    def __init__(self, versions: list[BinaryWorkbenchVersionDTO], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_LOAD_TITLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.CONTENT_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.ROW_SPACING)
        title = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_LOAD_TITLE, self)
        title.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_LOAD_SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        self.items = QListWidget(self)
        self.items.setObjectName("binary-workbench-search-results")
        for version in versions:
            self.items.addItem(version.name)
        if self.items.count():
            self.items.setCurrentRow(0)
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self)
        ok.setObjectName("preferences-ok")
        ok.setFocusPolicy(Qt.StrongFocus)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.items)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def selected_name(self) -> str | None:
        current = self.items.currentItem()
        return current.text() if current is not None else None


class BinaryWorkbenchVersionActionsDialog(QDialog):
    LOAD = "load"
    CHANGE = "change"
    UPDATE = "update"
    CREATE = "create"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._action: str | None = None
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_TITLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.CONTENT_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT.ACTION_BUTTON_SPACING)
        for text, action in (
            (BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_LOAD_TITLE, self.LOAD),
            (BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_CHANGE_TITLE, self.CHANGE),
            (BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_UPDATE_TITLE, self.UPDATE),
            (BINARY_WORKBENCH_FILE_DIALOG_TEXT.VERSION_CREATE_TITLE, self.CREATE),
        ):
            button = QPushButton(text, self)
            button.setObjectName("preferences-ok")
            button.setFocusPolicy(Qt.StrongFocus)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _, value=action: self._choose(value))
            layout.addWidget(button)

    def selected_action(self) -> str | None:
        return self._action

    def _choose(self, action: str) -> None:
        self._action = action
        self.accept()
