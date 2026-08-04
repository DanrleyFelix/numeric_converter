from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.action_controls import configure_binary_workbench_dialog_action
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_DIALOG_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.dialog_context_menu import configure_dialog_text_context_menu
from src.presentation.ui.components.binary_workbench.environment.offset_regions.constants import OFFSET_REGIONS_SIZE, OFFSET_REGIONS_SPACING


class OffsetRegionDetailsDialog(QDialog):
    """Edit the free-form details attached to one offset region."""

    def __init__(self, details: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.DETAILS)
        self.setFixedSize(OFFSET_REGIONS_SIZE.DETAILS_DIALOG_WIDTH, OFFSET_REGIONS_SIZE.DETAILS_DIALOG_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.CONTENT_MARGINS)
        layout.setSpacing(OFFSET_REGIONS_SPACING.DETAILS_DIALOG)
        self.editor = QPlainTextEdit(self)
        configure_dialog_text_context_menu(self.editor)
        self.editor.setPlainText(details)
        layout.addWidget(self.editor, 1)
        footer = QHBoxLayout()
        cancel = _details_action(BINARY_WORKBENCH_TEXT.CANCEL, self)
        confirm = _details_action(BINARY_WORKBENCH_TEXT.OK, self)
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self.accept)
        footer.addWidget(cancel)
        footer.addStretch(1)
        footer.addWidget(confirm)
        layout.addLayout(footer)

    def details(self) -> str:
        """Return the current details text."""

        return self.editor.toPlainText()


def _details_action(text: str, parent: QWidget) -> QPushButton:
    """Create a fixed details-dialog action."""

    button = QPushButton(text, parent)
    configure_binary_workbench_dialog_action(button)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button
