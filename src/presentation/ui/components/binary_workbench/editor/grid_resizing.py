from PySide6.QtCore import QTimer

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT


class GridResizingMixin:
    def _resize_editors(self) -> None:
        editors = [*self._offset_editors.values(), self.raw_instructions, self.bytes, self.instructions]
        for editor in editors:
            editor.setMinimumHeight(BINARY_WORKBENCH_LAYOUT.EDITOR_MIN_HEIGHT)

    def _schedule_layout_refresh(self) -> None:
        if self._layout_refresh_scheduled:
            return
        self._layout_refresh_scheduled = True
        QTimer.singleShot(0, self._run_scheduled_layout_refresh)

    def _run_scheduled_layout_refresh(self) -> None:
        self._layout_refresh_scheduled = False
        self._refresh_layout()

    def _refresh_layout(self) -> None:
        if self._updating:
            self._schedule_layout_refresh()
            return
        self._resize_editors()
        self.canvas_layout.activate()
        self._configure_scrollbar()
        if self._virtual:
            self.visibleWindowRequested.emit(
                self._aligned_scroll_offset(self.scrollbar.value()),
                self.visible_size(),
                1,
            )
        else:
            self._render_static_window()

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
        frame = editor.frameWidth() * 2
        expected_height = max(0, self._editor_viewport_height() - frame)
        viewport_height = max(editor.viewport().height(), expected_height)
        return max(1, viewport_height - (BINARY_WORKBENCH_LAYOUT.EDITOR_DOCUMENT_MARGIN * 2))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._schedule_layout_refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_layout()

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
            self.offsets_layout.addWidget(shell, 0)
