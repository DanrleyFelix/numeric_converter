from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QResizeEvent

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.editor.folding.gutter import LabelFoldGutter


class EditorLabelFoldingMixin:
    """Provide gutter geometry and visible-label marker lookup for an editor."""

    def _setup_label_folding(self) -> None:
        """Create the initially hidden fold gutter and its row state."""
        self._label_fold_regions: dict[int, tuple[str, bool]] = {}
        self._directive_fold_region: tuple[int, bool] | None = None
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

    def set_directive_fold_region(self, region: tuple[int, bool] | None) -> None:
        """Replace the optional leading debugger-directive fold marker."""
        self._directive_fold_region = region
        self._label_fold_gutter.update()

    def is_directive_fold_marker(self, block_number: int) -> bool:
        """Return whether a gutter marker controls the directive group."""

        region = self._directive_fold_region
        return region is not None and region[0] == block_number

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
            block_number = block.blockNumber()
            details = self._label_fold_regions.get(block_number)
            directive = self._directive_fold_region
            if details is None and directive is not None and directive[0] == block_number:
                details = ("", directive[1])
            if block.isVisible() and details is not None and top + height >= 0:
                markers.append(
                    (
                        block_number,
                        QRect(0, top, self._label_fold_gutter.width(), height),
                        details[1],
                    )
                )
            block = block.next()
        return markers

    def label_fold_marker_at(self, y: int) -> tuple[int, QRect, bool] | None:
        """Return the fold marker occupying a gutter y coordinate."""
        return next(
            (
                marker
                for marker in self.visible_label_fold_markers()
                if marker[1].top() <= y < marker[1].bottom()
            ),
            None,
        )

    def request_label_fold_toggle(self, block_number: int) -> None:
        """Emit the label represented by a gutter block for grid handling."""
        details = self._label_fold_regions.get(block_number)
        if self.is_directive_fold_marker(block_number):
            self.directiveFoldToggled.emit()
            return
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
            self._label_fold_gutter.update(
                0,
                rect.y(),
                self._label_fold_gutter.width(),
                rect.height(),
            )
