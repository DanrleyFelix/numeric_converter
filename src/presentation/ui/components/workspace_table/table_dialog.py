from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from src.presentation.ui.components.workspace_table.constants import (
    WORKSPACE_TABLE_MARGIN,
    WORKSPACE_TABLE_SIZE,
    WORKSPACE_TABLE_SPACING,
)
from src.presentation.ui.components.workspace_table.row_widget import WorkspaceRowWidget
from src.presentation.ui.components.workspace_table.rows import WorkspaceRow


class WorkspaceTableDialog(QDialog):
    removeRequested = Signal(object)

    def __init__(self, title: str, headers: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(title)
        self.setModal(False)
        self.setMinimumSize(WORKSPACE_TABLE_SIZE.MIN_WIDTH, WORKSPACE_TABLE_SIZE.MIN_HEIGHT)
        self.resize(WORKSPACE_TABLE_SIZE.DEFAULT_WIDTH, WORKSPACE_TABLE_SIZE.DEFAULT_HEIGHT)
        self.setSizeGripEnabled(True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        self._headers = list(headers)
        self._row_widgets: list[WorkspaceRowWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            WORKSPACE_TABLE_MARGIN.DIALOG_LEFT,
            WORKSPACE_TABLE_MARGIN.DIALOG_TOP,
            WORKSPACE_TABLE_MARGIN.DIALOG_RIGHT,
            WORKSPACE_TABLE_MARGIN.DIALOG_BOTTOM,
        )
        layout.setSpacing(WORKSPACE_TABLE_SPACING.DIALOG)

        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        self.header = QWidget(self.shell)
        self.header.setObjectName("workspace-table-header")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(
            WORKSPACE_TABLE_MARGIN.HEADER_LEFT,
            WORKSPACE_TABLE_MARGIN.HEADER_TOP,
            WORKSPACE_TABLE_MARGIN.HEADER_RIGHT,
            WORKSPACE_TABLE_MARGIN.HEADER_BOTTOM,
        )
        header_layout.setSpacing(WORKSPACE_TABLE_SPACING.HEADER)

        self.header_spacer = QWidget(self.header)
        self.header_spacer.setObjectName("workspace-table-header-spacer")
        self.header_spacer.setFixedWidth(WORKSPACE_TABLE_SIZE.HEADER_REMOVE_GAP)
        header_layout.addWidget(self.header_spacer, 0)

        self.header_labels = QWidget(self.header)
        header_labels_layout = QHBoxLayout(self.header_labels)
        header_labels_layout.setContentsMargins(
            WORKSPACE_TABLE_MARGIN.HEADER_LABEL_LEFT,
            WORKSPACE_TABLE_MARGIN.HEADER_LABEL_TOP,
            WORKSPACE_TABLE_MARGIN.HEADER_LABEL_RIGHT,
            WORKSPACE_TABLE_MARGIN.HEADER_LABEL_BOTTOM,
        )
        header_labels_layout.setSpacing(0)
        self.header_labels.setObjectName("workspace-header-labels")
        for text in self._headers:
            label = QLabel(text, self.header_labels)
            label.setObjectName("workspace-table-header-cell")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            header_labels_layout.addWidget(label, 1)
        header_layout.addWidget(self.header_labels, 1)
        shell_layout.addWidget(self.header)

        self.body_scroll = QScrollArea(self.shell)
        self.body_scroll.setObjectName("workspace-table-body-scroll")
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setFrameShape(QFrame.NoFrame)
        self.body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.body_scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")

        self.body = QWidget(self.body_scroll)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(
            WORKSPACE_TABLE_MARGIN.BODY_LEFT,
            WORKSPACE_TABLE_MARGIN.BODY_TOP,
            WORKSPACE_TABLE_MARGIN.BODY_RIGHT,
            WORKSPACE_TABLE_MARGIN.BODY_BOTTOM,
        )
        self.body_layout.setSpacing(WORKSPACE_TABLE_SPACING.BODY)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.body_layout.addStretch(1)
        self.body_scroll.setWidget(self.body)
        shell_layout.addWidget(self.body_scroll, 1)

        layout.addWidget(self.shell, 1)

    @property
    def row_widgets(self) -> list[WorkspaceRowWidget]:
        return list(self._row_widgets)

    def set_rows(self, rows: list[WorkspaceRow]) -> None:
        self._row_widgets.clear()
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for row in rows:
            row_widget = WorkspaceRowWidget(row, self.body)
            row_widget.removeRequested.connect(self.removeRequested.emit)
            self.body_layout.addWidget(row_widget)
            self._row_widgets.append(row_widget)

        self.body_layout.addStretch(1)
