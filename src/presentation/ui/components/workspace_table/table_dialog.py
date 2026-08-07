from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.presentation.ui.components.workspace_table.constants import (
    WORKSPACE_TABLE_MARGIN,
    WORKSPACE_TABLE_SIZE,
    WORKSPACE_TABLE_SPACING,
)
from src.presentation.ui.components.workspace_table.model import (
    WorkspaceFilterProxyModel,
    WorkspaceTableModel,
)
from src.presentation.ui.components.workspace_table.rows import WorkspaceRow
from src.presentation.ui.design.icons import Icons


class WorkspaceTableDialog(QDialog):
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

    def _build_ui(self, allow_add: bool) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            WORKSPACE_TABLE_MARGIN.DIALOG_LEFT,
            WORKSPACE_TABLE_MARGIN.DIALOG_TOP,
            WORKSPACE_TABLE_MARGIN.DIALOG_RIGHT,
            WORKSPACE_TABLE_MARGIN.DIALOG_BOTTOM,
        )
        root.setSpacing(WORKSPACE_TABLE_SPACING.SECTIONS)
        if allow_add:
            root.addWidget(self._entry_row())
        self.table = QTableView(self)
        self.table.setObjectName("workspace-model-table")
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(WORKSPACE_TABLE_SIZE.ROW_HEIGHT)
        self.table.horizontalHeader().setObjectName("workspace-model-header")
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.selectionModel().selectionChanged.connect(self._update_remove_state)
        root.addWidget(self.table, 1)
        root.addWidget(self._footer_row(include_remove=not allow_add))

    def _entry_row(self) -> QFrame:
        frame = QFrame(self)
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(WORKSPACE_TABLE_SPACING.CONTROLS)
        self.name_input = self._line_edit("Name")
        self.value_input = self._line_edit("Value")
        add = self._button("Add", Icons.add())
        add.clicked.connect(self._emit_add)
        self.remove_button = self._button("Remove", Icons.remove())
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self._emit_remove)
        row.addWidget(self.name_input, 1)
        row.addWidget(self.value_input, 1)
        row.addWidget(add)
        row.addStretch(1)
        row.addWidget(self.remove_button)
        return frame

    def _footer_row(self, *, include_remove: bool) -> QFrame:
        frame = QFrame(self)
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(WORKSPACE_TABLE_SPACING.CONTROLS)
        if include_remove:
            self.remove_button = self._button("Remove", Icons.remove())
            self.remove_button.setEnabled(False)
            self.remove_button.clicked.connect(self._emit_remove)
        self.filter_input = self._line_edit("Filter")
        self.filter_input.addAction(Icons.search_muted(), QLineEdit.ActionPosition.TrailingPosition)
        self.filter_input.textChanged.connect(self.proxy.setFilterFixedString)
        if include_remove:
            row.addWidget(self.remove_button)
        row.addWidget(self.filter_input, 1)
        return frame

    def _line_edit(self, placeholder: str) -> QLineEdit:
        editor = QLineEdit(self)
        editor.setObjectName("workspace-model-input")
        editor.setPlaceholderText(placeholder)
        editor.setMinimumWidth(WORKSPACE_TABLE_SIZE.FIELD_MIN_WIDTH)
        editor.setFixedHeight(WORKSPACE_TABLE_SIZE.CONTROL_HEIGHT)
        return editor

    def _button(self, text: str, icon) -> QPushButton:
        button = QPushButton(text, self)
        button.setObjectName("workspace-model-action")
        button.setIcon(icon)
        button.setIconSize(QSize(WORKSPACE_TABLE_SIZE.ICON_SIZE, WORKSPACE_TABLE_SIZE.ICON_SIZE))
        button.setFixedSize(
            WORKSPACE_TABLE_SIZE.ACTION_WIDTH,
            WORKSPACE_TABLE_SIZE.CONTROL_HEIGHT,
        )
        return button

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
