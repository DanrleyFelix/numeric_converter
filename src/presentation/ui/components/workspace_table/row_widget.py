from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from src.presentation.ui.components.workspace_table.constants import (
    WORKSPACE_TABLE_MARGIN,
    WORKSPACE_TABLE_SIZE,
    WORKSPACE_TABLE_SPACING,
)
from src.presentation.ui.components.workspace_table.rows import WorkspaceRow
from src.presentation.ui.design.icons import Icons


class WorkspaceRowWidget(QWidget):
    removeRequested = Signal(object)

    def __init__(self, row: WorkspaceRow, parent: QWidget | None = None):
        super().__init__(parent)
        self._row = row
        self.setObjectName("workspace-row")
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(WORKSPACE_TABLE_SIZE.ROW_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(WORKSPACE_TABLE_SPACING.ROW)

        self.remove_button = QPushButton(self)
        self.remove_button.setObjectName("workspace-row-remove")
        self._remove_icon = Icons.remove()
        self._remove_hover_icon = Icons.remove_hover()
        self.remove_button.setIcon(self._remove_icon)
        self.remove_button.setIconSize(
            QSize(
                WORKSPACE_TABLE_SIZE.REMOVE_ICON_SIZE,
                WORKSPACE_TABLE_SIZE.REMOVE_ICON_SIZE,
            )
        )
        self.remove_button.setText("")
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.setFocusPolicy(Qt.NoFocus)
        self.remove_button.installEventFilter(self)
        self.remove_button.setFixedSize(
            WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH,
            WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT,
        )
        self.remove_button.clicked.connect(lambda: self.removeRequested.emit(self._row.key))
        layout.addWidget(self.remove_button, 0, Qt.AlignVCenter)

        self.card = QFrame(self)
        self.card.setObjectName("workspace-row-card")
        self.card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(
            WORKSPACE_TABLE_MARGIN.CARD_LEFT,
            WORKSPACE_TABLE_MARGIN.CARD_TOP,
            WORKSPACE_TABLE_MARGIN.CARD_RIGHT,
            WORKSPACE_TABLE_MARGIN.CARD_BOTTOM,
        )
        card_layout.setSpacing(WORKSPACE_TABLE_SPACING.CARD)

        self._labels: list[QLabel] = []
        for value in row.values:
            label = QLabel(value, self.card)
            label.setObjectName("workspace-row-cell")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setTextInteractionFlags(
                Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
            )
            label.setCursor(Qt.IBeamCursor)
            label.setFocusPolicy(Qt.ClickFocus)
            card_layout.addWidget(label, 1)
            self._labels.append(label)

        layout.addWidget(self.card, 1)

    @property
    def values(self) -> tuple[str, ...]:
        return tuple(label.text() for label in self._labels)

    @property
    def cell_labels(self) -> tuple[QLabel, ...]:
        return tuple(self._labels)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.remove_button:
            if event.type() == QEvent.Enter:
                self.remove_button.setIcon(self._remove_hover_icon)
            elif event.type() == QEvent.Leave:
                self.remove_button.setIcon(self._remove_icon)
        return super().eventFilter(watched, event)
