from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT,
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)


class BinaryWorkbenchInternalFileDialog(QDialog):
    def __init__(self, internal_files: list[BinaryWorkbenchInternalFileDTO], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.INTERNAL_TITLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.DIALOG_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_DIALOG_LAYOUT.SECTION_SPACING)
        self.items = QListWidget(self)
        self.items.setObjectName("binary-workbench-internal-files")
        self.items.setSelectionMode(QAbstractItemView.SingleSelection)
        self.items.setFocusPolicy(Qt.NoFocus)
        self.items.setUniformItemSizes(True)
        for item in internal_files:
            widget_item = QListWidgetItem(item.name)
            widget_item.setSizeHint(
                QSize(0, BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT.ITEM_HEIGHT)
            )
            self.items.addItem(widget_item)
        self.items.setFixedHeight(self._list_height(len(internal_files)))
        self.items.itemDoubleClicked.connect(lambda _item: self.accept())
        footer = QWidget(self)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(*BINARY_WORKBENCH_DIALOG_LAYOUT.EMPTY_MARGINS)
        cancel = QPushButton(BINARY_WORKBENCH_TEXT.CANCEL, footer)
        ok = QPushButton(BINARY_WORKBENCH_FILE_DIALOG_TEXT.OK, self)
        for button in (cancel, ok):
            configure_binary_workbench_dialog_action(button)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        ok.setEnabled(False)
        self.items.currentItemChanged.connect(
            lambda current, _previous: ok.setEnabled(current is not None)
        )
        footer_layout.addWidget(cancel, 0, Qt.AlignLeft)
        footer_layout.addStretch(1)
        footer_layout.addWidget(ok, 0, Qt.AlignRight)
        layout.addWidget(self.items)
        layout.addWidget(footer)
        preferred = self.sizeHint()
        self.setFixedSize(
            preferred.width()
            + BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT.WIDTH_INCREMENT,
            preferred.height(),
        )

    def selected_name(self) -> str | None:
        current = self.items.currentItem()
        return current.text() if current is not None else None

    def _list_height(self, item_count: int) -> int:
        visible_items = min(
            max(1, item_count),
            BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT.MAX_VISIBLE_ITEMS,
        )
        return (
            visible_items * BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT.ITEM_HEIGHT
            + BINARY_WORKBENCH_INTERNAL_FILE_DIALOG_LAYOUT.LIST_FRAME_WIDTH
        )
