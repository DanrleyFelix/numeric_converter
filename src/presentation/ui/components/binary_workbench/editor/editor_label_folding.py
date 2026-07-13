from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QIcon, QMouseEvent, QPaintEvent, QPainter, QResizeEvent
from PySide6.QtWidgets import QToolTip, QWidget

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.design.icons import Icons


class LabelFoldGutter(QWidget):
    """Paint and activate fold controls beside assembly label lines."""

    def __init__(self, editor) -> None:
        super().__init__(editor)
        self._editor = editor
        self._hovered_block = -1
        self.setMouseTracking(True)

    def sizeHint(self):
        """Return the fixed width reserved for label fold controls."""
        hint = super().sizeHint()
        hint.setWidth(BINARY_WORKBENCH_LAYOUT.EDITOR_LABEL_FOLD_GUTTER_WIDTH)
        return hint

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw one circular plus or minus icon for each visible label."""
        del event
        painter = QPainter(self)
        for block_number, line_rect, collapsed in self._editor.visible_label_fold_markers():
            icon = Icons.expand_circle() if collapsed else Icons.collapse_circle()
            mode = QIcon.Active if block_number == self._hovered_block else QIcon.Normal
            icon.paint(painter, self._icon_rect(line_rect), Qt.AlignCenter, mode, QIcon.Off)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Show pointer feedback and a tooltip over a fold control."""
        marker = self._editor.label_fold_marker_at(event.position().toPoint().y())
        self._set_hovered_block(marker[0] if marker is not None else -1)
        if marker is None:
            QToolTip.hideText()
            return
        tooltip = (
            BINARY_WORKBENCH_TEXT.EXPAND_LABEL
            if marker[2]
            else BINARY_WORKBENCH_TEXT.COLLAPSE_LABEL
        )
        QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Toggle the label body represented by the clicked control."""
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
        """Center the configured icon size within a label line."""
        size = BINARY_WORKBENCH_LAYOUT.EDITOR_LABEL_FOLD_ICON_SIZE
        left = (self.width() - size) // 2
        top = line_rect.top() + max(0, (line_rect.height() - size) // 2)
        return QRect(left, top, size, size)


class EditorLabelFoldingMixin:
    """Provide gutter geometry and visible-label marker lookup for an editor."""

    def _setup_label_folding(self) -> None:
        """Create the initially hidden fold gutter and its row state."""
        self._label_fold_regions: dict[int, tuple[str, bool]] = {}
        self._label_fold_gutter = LabelFoldGutter(self)
        self._label_fold_gutter.hide()
        self.updateRequest.connect(self._update_label_fold_gutter)

    def set_label_folding_enabled(self, enabled: bool) -> None:
        """Show or hide the assembly label fold gutter."""
        width = BINARY_WORKBENCH_LAYOUT.EDITOR_LABEL_FOLD_GUTTER_WIDTH if enabled else 0
        self.setViewportMargins(width, 0, 0, 0)
        self._label_fold_gutter.setVisible(enabled)
        self._position_label_fold_gutter()

    def set_label_fold_regions(self, regions: dict[int, tuple[str, bool]]) -> None:
        """Replace the label rows and collapsed state shown by the gutter."""
        self._label_fold_regions = dict(regions)
        self._label_fold_gutter.update()

    def visible_label_fold_markers(self) -> list[tuple[int, QRect, bool]]:
        """Return visible label blocks with viewport-aligned rectangles."""
        markers: list[tuple[int, QRect, bool]] = []
        block = self.firstVisibleBlock()
        viewport_height = self.viewport().height()
        while block.isValid():
            top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
            height = round(self.blockBoundingRect(block).height())
            if top > viewport_height:
                break
            details = self._label_fold_regions.get(block.blockNumber())
            if block.isVisible() and details is not None and top + height >= 0:
                markers.append(
                    (block.blockNumber(), QRect(0, top, self._label_fold_gutter.width(), height), details[1])
                )
            block = block.next()
        return markers

    def label_fold_marker_at(self, y: int) -> tuple[int, QRect, bool] | None:
        """Return the fold marker occupying a gutter y coordinate."""
        return next(
            (marker for marker in self.visible_label_fold_markers() if marker[1].top() <= y < marker[1].bottom()),
            None,
        )

    def request_label_fold_toggle(self, block_number: int) -> None:
        """Emit the label represented by a gutter block for grid handling."""
        details = self._label_fold_regions.get(block_number)
        if details is not None:
            self.labelFoldToggled.emit(details[0])

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the fold gutter aligned with the editor contents rectangle."""
        super().resizeEvent(event)
        self._position_label_fold_gutter()

    def _position_label_fold_gutter(self) -> None:
        """Place the gutter in the reserved left viewport margin."""
        rect = self.contentsRect()
        self._label_fold_gutter.setGeometry(
            QRect(
                rect.left(),
                rect.top(),
                BINARY_WORKBENCH_LAYOUT.EDITOR_LABEL_FOLD_GUTTER_WIDTH,
                rect.height(),
            )
        )

    def _update_label_fold_gutter(self, rect: QRect, dy: int) -> None:
        """Repaint or scroll the gutter with the editor viewport."""
        if dy:
            self._label_fold_gutter.scroll(0, dy)
        else:
            self._label_fold_gutter.update(0, rect.y(), self._label_fold_gutter.width(), rect.height())
