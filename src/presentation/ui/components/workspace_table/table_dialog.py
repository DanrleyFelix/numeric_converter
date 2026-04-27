from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from src.presentation.ui.components.workspace_table.row_widget import WorkspaceRowWidget
from src.presentation.ui.components.workspace_table.rows import WorkspaceRow


class WorkspaceTableDialog(QDialog):
    removeRequested = Signal(object)

    _SCROLLBAR_QSS = """
QScrollBar:vertical {
    background: rgba(8, 12, 20, 0.96);
    border: 1px solid rgba(25, 47, 88, 0.96);
    border-radius: 10px;
    width: 14px;
    margin: 10px 8px 10px 0px;
}
QScrollBar::handle:vertical {
    background: rgba(39, 84, 162, 0.96);
    border-radius: 8px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(58, 108, 190, 1.0);
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: rgba(8, 12, 20, 0.96);
    border-radius: 10px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical {
    width: 0px;
    height: 0px;
    background: transparent;
    border: none;
}
"""

    def __init__(self, title: str, headers: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(title)
        self.setModal(False)
        self.setMinimumSize(700, 400)
        self.resize(820, 520)
        self.setSizeGripEnabled(True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        self._headers = list(headers)
        self._row_widgets: list[WorkspaceRowWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_label = QLabel(title, self)
        title_label.setObjectName("workspace-table-title")
        layout.addWidget(title_label)

        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        self.header = QWidget(self.shell)
        self.header.setObjectName("workspace-table-header")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(18, 0, 18, 0)
        header_layout.setSpacing(14)

        self.header_spacer = QWidget(self.header)
        self.header_spacer.setObjectName("workspace-table-header-spacer")
        self.header_spacer.setFixedWidth(34)
        header_layout.addWidget(self.header_spacer, 0)

        self.header_labels = QWidget(self.header)
        header_labels_layout = QHBoxLayout(self.header_labels)
        header_labels_layout.setContentsMargins(16, 14, 16, 14)
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
        self.body_scroll.verticalScrollBar().setStyleSheet(self._SCROLLBAR_QSS)

        self.body = QWidget(self.body_scroll)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(18, 16, 18, 16)
        self.body_layout.setSpacing(10)
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
