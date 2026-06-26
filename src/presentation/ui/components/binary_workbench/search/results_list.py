from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QApplication, QListWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT


class SearchResultsList(QListWidget):
    offsetActivated = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("binary-workbench-search-results")
        self.setFocusPolicy(Qt.NoFocus)
        self.setMouseTracking(True)
        self.setSpacing(BINARY_WORKBENCH_LAYOUT.SEARCH_RESULT_ITEM_SPACING)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.itemClicked.connect(lambda item: self.offsetActivated.emit(int(item.text(), 0)))
        self.itemDoubleClicked.connect(lambda item: _copy_offset_text(item.text()))

    def eventFilter(self, watched, event) -> bool:
        if watched is self.viewport():
            if event.type() == QEvent.Type.MouseMove:
                point = event.position().toPoint() if hasattr(event, "position") else event.pos()
                cursor = Qt.PointingHandCursor if self.itemAt(point) is not None else Qt.ArrowCursor
                self.viewport().setCursor(cursor)
            elif event.type() == QEvent.Type.Leave:
                self.viewport().unsetCursor()
        return super().eventFilter(watched, event)


def _copy_offset_text(value: str) -> None:
    QApplication.clipboard().setText(value.removeprefix("0x").removeprefix("0X"))
