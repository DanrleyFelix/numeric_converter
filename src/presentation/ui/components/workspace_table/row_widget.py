from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.presentation.ui.components.workspace_table.rows import WorkspaceRow


class WorkspaceRowWidget(QWidget):
    removeRequested = Signal(object)

    def __init__(self, row: WorkspaceRow, parent: QWidget | None = None):
        super().__init__(parent)
        self._row = row
        self.setObjectName("workspace-row")
        self.setAttribute(Qt.WA_Hover, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.remove_button = QPushButton("-", self)
        self.remove_button.setObjectName("workspace-row-remove")
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.setFocusPolicy(Qt.NoFocus)
        self.remove_button.setFixedSize(34, 24)
        self.remove_button.clicked.connect(lambda: self.removeRequested.emit(self._row.key))
        layout.addWidget(self.remove_button, 0, Qt.AlignVCenter)

        self.card = QFrame(self)
        self.card.setObjectName("workspace-row-card")
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(0)

        self._labels: list[QLabel] = []
        for value in row.values:
            label = QLabel(value, self.card)
            label.setObjectName("workspace-row-cell")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            card_layout.addWidget(label, 1)
            self._labels.append(label)

        layout.addWidget(self.card, 1)

    @property
    def values(self) -> tuple[str, ...]:
        return tuple(label.text() for label in self._labels)
