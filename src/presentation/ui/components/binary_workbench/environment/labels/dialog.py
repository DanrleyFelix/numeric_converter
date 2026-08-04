from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QSizePolicy, QVBoxLayout

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_filter,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_input,
)
from src.presentation.ui.components.binary_workbench.environment_table.model import (
    EnvironmentFilterProxyModel,
    EnvironmentTableModel,
)
from src.presentation.ui.components.binary_workbench.environment_table.view import (
    EnvironmentCellDelegate,
    EnvironmentTableView,
    configure_environment_table,
)


class BinaryWorkbenchLabelsDialog(QDialog):
    """Browse labels through a virtualized, filterable table."""

    goToRequested = Signal(int)

    def __init__(self, labels: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.LABELS)
        self.setFixedWidth(BINARY_WORKBENCH_LAYOUT.LABELS_DIALOG_WIDTH)
        self.setMinimumHeight(BINARY_WORKBENCH_LAYOUT.FILE_DIALOG_MIN_HEIGHT)
        self.setMaximumHeight(BINARY_WORKBENCH_LAYOUT.LABELS_DIALOG_MAX_HEIGHT)
        self.resize(BINARY_WORKBENCH_LAYOUT.LABELS_DIALOG_WIDTH, BINARY_WORKBENCH_LAYOUT.FILE_DIALOG_HEIGHT)
        self.labels_model = EnvironmentTableModel(
            (BINARY_WORKBENCH_TEXT.LABEL_NAME, BINARY_WORKBENCH_TEXT.OFFSET),
            set(),
            self,
        )
        self.labels_proxy = EnvironmentFilterProxyModel(self)
        self.labels_proxy.setSourceModel(self.labels_model)
        self._build_dialog(labels)

    def _build_dialog(self, labels: dict[str, str]) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(*ENVIRONMENT_LAYOUT.DIALOG_MARGINS)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        layout = QVBoxLayout(self.shell)
        layout.setContentsMargins(*ENVIRONMENT_LAYOUT.SYMBOLS_PANEL_MARGINS)
        layout.setSpacing(ENVIRONMENT_LAYOUT.PANEL_SPACING)
        self.table = EnvironmentTableView(self.shell)
        self.table.setModel(self.labels_proxy)
        self.table.setItemDelegate(EnvironmentCellDelegate(parent=self.table))
        configure_environment_table(self.table, "binary-workbench-environment-table")
        self.table.doubleClicked.connect(lambda _index: self._go_to_selected())
        rows = [([name, offset], int(offset, 0), "") for name, offset in sorted(labels.items(), key=lambda item: int(item[1], 0))]
        self.labels_model.replace(rows)
        layout.addWidget(self.table, 1)
        self._build_footer(layout)
        root.addWidget(self.shell, 1)

    def _build_footer(self, parent: QVBoxLayout) -> None:
        footer = QFrame(self.shell)
        row = QHBoxLayout(footer)
        row.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        row.setSpacing(ENVIRONMENT_LAYOUT.ROW_SPACING)
        self.filter_input = symbol_input(BINARY_WORKBENCH_TEXT.FILTER, footer, search_icon=True)
        configure_binary_workbench_filter(self.filter_input)
        configure_binary_workbench_line_edit(self.filter_input)
        self.filter_input.setMinimumWidth(0)
        self.filter_input.setMaximumWidth(BINARY_WORKBENCH_LAYOUT.LABELS_DIALOG_WIDTH)
        self.filter_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_input.textChanged.connect(self._apply_filter)
        row.addWidget(self.filter_input, 1)
        parent.addWidget(footer)

    def _selected_record(self):
        """Return the selected source record after proxy mapping."""

        index = self.table.currentIndex()
        return None if not index.isValid() else self.labels_model.record_at(self.labels_proxy.mapToSource(index).row())

    def _apply_filter(self) -> None:
        """Filter label name and offset together."""

        self.labels_proxy.set_query(self.filter_input.text())

    def _go_to_selected(self) -> None:
        """Navigate to the selected label's stored numeric offset."""

        record = self._selected_record()
        if record is not None and isinstance(record.payload, int):
            self.goToRequested.emit(record.payload)
