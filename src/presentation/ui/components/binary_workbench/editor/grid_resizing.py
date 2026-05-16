from PySide6.QtCore import Qt

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT


class GridResizingMixin:
    def _resize_editors(self) -> None:
        editors = [*self._offset_editors.values(), self.bytes, self.instructions]
        height = self._editor_viewport_height()
        for editor in editors:
            editor.setFixedHeight(height)

    def _visible_row_count(self) -> int:
        line_height = max(1, self.instructions.fontMetrics().lineSpacing())
        available = self._usable_editor_height(self.instructions)
        rows = max(1, (available // line_height) - BINARY_WORKBENCH_LAYOUT.EDITOR_VISIBLE_ROW_SAFETY)
        return min(BINARY_WORKBENCH_LAYOUT.EDITOR_MAX_VISIBLE_ROWS, rows)

    def _editor_viewport_height(self) -> int:
        return max(
            BINARY_WORKBENCH_LAYOUT.EDITOR_MIN_HEIGHT,
            self.height() - BINARY_WORKBENCH_LAYOUT.EDITOR_PANEL_HEADER_HEIGHT,
        )

    def _usable_editor_height(self, editor) -> int:
        viewport_height = editor.viewport().height()
        if viewport_height <= 0:
            frame = editor.frameWidth() * 2
            viewport_height = max(0, self._editor_viewport_height() - frame)
        return max(1, viewport_height - (BINARY_WORKBENCH_LAYOUT.EDITOR_DOCUMENT_MARGIN * 2))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_editors()
        self._configure_scrollbar()
        if self._virtual:
            self.visibleWindowRequested.emit(
                self._aligned_scroll_offset(self.scrollbar.value()),
                self.visible_size(),
                1,
            )
        else:
            self._render_static_window()

    def _sync_offset_columns(self, names: list[str]) -> None:
        if names == self._columns:
            return
        self._columns = names
        self._offset_editors.clear()
        while self.offsets_layout.count():
            item = self.offsets_layout.takeAt(0)
            if widget := item.widget():
                widget.setParent(None)
                widget.deleteLater()
        for name in names:
            display_label = BINARY_WORKBENCH_TEXT.FILE_OFFSET if name == BINARY_WORKBENCH_TEXT.FILE else name
            shell, editor = self._panel(
                display_label,
                "binary-workbench-offsets-panel",
                True,
                BINARY_WORKBENCH_LAYOUT.EDITOR_OFFSET_WIDTH,
            )
            self._offset_editors[name] = editor
            self.offsets_layout.addWidget(shell, 0, Qt.AlignTop)
