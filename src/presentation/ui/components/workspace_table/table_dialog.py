from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QWidget

from src.presentation.ui.components.workspace_table.constants import WORKSPACE_TABLE_SIZE
from src.presentation.ui.components.workspace_table.model import (
    WorkspaceFilterProxyModel,
    WorkspaceTableModel,
)
from src.presentation.ui.components.workspace_table.rows import WorkspaceRow
from src.presentation.ui.components.workspace_table.view import WorkspaceTableLayoutMixin


class WorkspaceTableDialog(WorkspaceTableLayoutMixin, QDialog):
    """Model/View Numeric Variables or Logs dialog with constant widget count."""

    removeManyRequested = Signal(tuple)
    addRequested = Signal(str, str)
    sizePersistRequested = Signal(int, int)

    def __init__(
        self,
        title: str,
        headers: list[str],
        parent: QWidget | None = None,
        *,
        allow_add: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(title)
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(WORKSPACE_TABLE_SIZE.MIN_WIDTH, WORKSPACE_TABLE_SIZE.MIN_HEIGHT)
        self.resize(WORKSPACE_TABLE_SIZE.DEFAULT_WIDTH, WORKSPACE_TABLE_SIZE.DEFAULT_HEIGHT)
        self.setSizeGripEnabled(True)

        self.model = WorkspaceTableModel(tuple(headers), self)
        self.proxy = WorkspaceFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self._build_ui(allow_add)

    @property
    def row_widgets(self) -> list[QWidget]:
        """Legacy probe: virtualized tables intentionally own no per-row widgets."""
        return []

    def set_rows(self, rows: list[WorkspaceRow]) -> None:
        self.model.replace_rows(rows)
        self._update_remove_state()

    def _selected_keys(self) -> tuple[object, ...]:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        keys: list[object] = []
        for row in rows:
            source = self.proxy.mapToSource(self.proxy.index(row, 0))
            keys.append(self.model.data(source, self.model.KEY_ROLE))
        return tuple(keys)

    def _emit_remove(self) -> None:
        keys = self._selected_keys()
        if keys:
            self.removeManyRequested.emit(keys)

    def _emit_add(self) -> None:
        name = self.name_input.text().strip()
        value = self.value_input.text().strip()
        if name and value:
            self.addRequested.emit(name, value)

    def _update_remove_state(self, *_args) -> None:
        self.remove_button.setEnabled(bool(self._selected_keys()))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.sizePersistRequested.emit(self.width(), self.height())
        super().closeEvent(event)
