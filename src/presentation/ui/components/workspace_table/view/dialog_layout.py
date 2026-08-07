from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
)

from src.presentation.ui.components.workspace_table.constants import (
    WORKSPACE_TABLE_MARGIN,
    WORKSPACE_TABLE_SIZE,
    WORKSPACE_TABLE_SPACING,
)
from src.presentation.ui.components.workspace_table.controls import (
    CenteredIconTextButton,
)
from src.presentation.ui.design.icons import Icons


class WorkspaceTableLayoutMixin:
    """Build Numeric Model/View dialogs with the Symbols visual proportions."""

    def _build_ui(self, allow_add: bool) -> None:
        """Create the breathing panel, fixed controls and square table."""

        root = QVBoxLayout(self)
        root.setContentsMargins(
            WORKSPACE_TABLE_MARGIN.DIALOG_LEFT,
            WORKSPACE_TABLE_MARGIN.DIALOG_TOP,
            WORKSPACE_TABLE_MARGIN.DIALOG_RIGHT,
            WORKSPACE_TABLE_MARGIN.DIALOG_BOTTOM,
        )
        root.setSpacing(0)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        content = QVBoxLayout(self.shell)
        content.setContentsMargins(
            WORKSPACE_TABLE_MARGIN.PANEL_LEFT,
            WORKSPACE_TABLE_MARGIN.PANEL_TOP,
            WORKSPACE_TABLE_MARGIN.PANEL_RIGHT,
            WORKSPACE_TABLE_MARGIN.PANEL_BOTTOM,
        )
        content.setSpacing(WORKSPACE_TABLE_SPACING.SECTIONS)
        if allow_add:
            content.addWidget(self._entry_row())
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
        content.addWidget(self.table, 1)
        content.addWidget(self._footer_row(include_remove=True))
        root.addWidget(self.shell, 1)

    def _entry_row(self) -> QFrame:
        """Build the symmetric Variables entry row."""

        frame = QFrame(self)
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(WORKSPACE_TABLE_SPACING.VARIABLE_ENTRY)
        self.name_input = self._line_edit("Name", expanding=True)
        self.value_input = self._line_edit("Value", expanding=True)
        self.add_button = self._button("Add", Icons.add())
        self.add_button.clicked.connect(self._emit_add)
        row.addWidget(self.name_input, 1)
        row.addWidget(self.value_input, 1)
        row.addWidget(self.add_button)
        return frame

    def _footer_row(self, *, include_remove: bool) -> QFrame:
        """Place Logs Remove beside the expanding filter."""

        frame = QFrame(self)
        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(WORKSPACE_TABLE_SPACING.CONTROLS)
        if include_remove:
            self.remove_button = self._button("Remove", Icons.remove())
            self.remove_button.setEnabled(False)
            self.remove_button.clicked.connect(self._emit_remove)
        self.filter_input = self._line_edit("Filter", expanding=True)
        self.filter_input.addAction(
            Icons.search_muted(),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self.filter_input.textChanged.connect(self.proxy.setFilterFixedString)
        if include_remove:
            row.addWidget(self.remove_button)
        row.addWidget(self.filter_input, 1)
        return frame

    def _line_edit(self, placeholder: str, *, expanding: bool = False) -> QLineEdit:
        """Create a rounded input using the shared Symbols height."""

        editor = QLineEdit(self)
        editor.setObjectName("workspace-model-input")
        editor.setPlaceholderText(placeholder)
        if expanding:
            editor.setMinimumWidth(WORKSPACE_TABLE_SIZE.FIELD_MIN_WIDTH)
            editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            editor.setFixedWidth(WORKSPACE_TABLE_SIZE.FIELD_MIN_WIDTH)
        editor.setFixedHeight(WORKSPACE_TABLE_SIZE.CONTROL_HEIGHT)
        return editor

    def _button(self, text: str, icon) -> QPushButton:
        """Create a centered icon/text action matching Symbols."""

        button = CenteredIconTextButton(
            text,
            WORKSPACE_TABLE_SIZE.ICON_TEXT_SPACING,
            self,
        )
        button.setObjectName("workspace-model-action")
        button.setIcon(icon)
        button.setIconSize(
            QSize(WORKSPACE_TABLE_SIZE.ICON_SIZE, WORKSPACE_TABLE_SIZE.ICON_SIZE)
        )
        button.setFixedSize(
            WORKSPACE_TABLE_SIZE.ACTION_WIDTH,
            WORKSPACE_TABLE_SIZE.CONTROL_HEIGHT,
        )
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button
