from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QIcon, QMouseEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import QToolTip, QWidget

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.design.icons import Icons


class LabelFoldGutter(QWidget):
    """Paint and activate fold controls beside assembly source groups."""

    def __init__(self, editor) -> None:
        super().__init__(editor)
        self._editor = editor
        self._hovered_block = -1
        self.setMouseTracking(True)

    def sizeHint(self):
        """Return the fixed width reserved for source fold controls."""

        hint = super().sizeHint()
        hint.setWidth(BINARY_WORKBENCH_LAYOUT.EDITOR_LABEL_FOLD_GUTTER_WIDTH)
        return hint

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw one circular plus or minus icon for each visible group."""

        del event
        painter = QPainter(self)
        for block_number, line_rect, collapsed in self._editor.visible_label_fold_markers():
            icon = Icons.expand_circle() if collapsed else Icons.collapse_circle()
            mode = QIcon.Active if block_number == self._hovered_block else QIcon.Normal
            icon.paint(painter, self._icon_rect(line_rect), Qt.AlignCenter, mode, QIcon.Off)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Show pointer feedback and the tooltip for the hovered group."""

        marker = self._editor.label_fold_marker_at(event.position().toPoint().y())
        self._set_hovered_block(marker[0] if marker is not None else -1)
        if marker is None:
            QToolTip.hideText()
            return
        directive = self._editor.is_directive_fold_marker(marker[0])
        if directive:
            tooltip = (
                BINARY_WORKBENCH_TEXT.EXPAND_DIRECTIVES
                if marker[2]
                else BINARY_WORKBENCH_TEXT.COLLAPSE_DIRECTIVES
            )
        else:
            tooltip = (
                BINARY_WORKBENCH_TEXT.EXPAND_LABEL
                if marker[2]
                else BINARY_WORKBENCH_TEXT.COLLAPSE_LABEL
            )
        QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Toggle the source group represented by the clicked control."""

        marker = self._editor.label_fold_marker_at(event.position().toPoint().y())
        if event.button() == Qt.LeftButton and marker is not None:
            self._editor.request_label_fold_toggle(marker[0])
            event.accept()
            return
        super().mousePressEvent(event)

    def leaveEvent(self, event) -> None:
        """Clear hover feedback when the pointer leaves the gutter."""

        self._set_hovered_block(-1)
        QToolTip.hideText()
        super().leaveEvent(event)

    def _set_hovered_block(self, block_number: int) -> None:
        """Update the highlighted control and pointer cursor."""

        if block_number == self._hovered_block:
            return
        self._hovered_block = block_number
        self.setCursor(Qt.PointingHandCursor if block_number >= 0 else Qt.ArrowCursor)
        self.update()

    def _icon_rect(self, line_rect: QRect) -> QRect:
        """Center the configured icon size within a source line."""

        size = BINARY_WORKBENCH_LAYOUT.EDITOR_LABEL_FOLD_ICON_SIZE
        left = (self.width() - size) // 2
        top = line_rect.top() + max(0, (line_rect.height() - size) // 2)
        return QRect(left, top, size, size)
