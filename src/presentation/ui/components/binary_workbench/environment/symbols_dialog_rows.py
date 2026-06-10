from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.environment.symbol_offsets_dialog import (
    BinaryWorkbenchSymbolOffsetsDialog,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    SymbolRemoveRowButton,
    symbol_button,
    symbol_input,
    symbol_kind_combo,
)
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class SymbolsDialogRowsMixin:
    def values(self) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        targets = {"Variable": {}, "Equate": {}}
        for kind, name, value, _ in self._rows:
            if name.text().strip() and value.text().strip():
                targets[kind.currentText()][name.text().strip()] = value.text().strip()
        return targets["Variable"], targets["Equate"], {}

    def _load_rows(self, variables: dict[str, str], equates: dict[str, str], labels: dict[str, str]) -> None:
        for kind, items in (("Variable", variables), ("Equate", equates)):
            for name, value in items.items():
                self._append_row(kind, str(name), str(value))

    def _append_from_entry(self) -> None:
        self._append_row(self.kind.currentText(), self.name.text(), self.value.text())
        self.name.clear()
        self.value.clear()

    def _clear_rows(self) -> None:
        for _, _, _, row in self._rows:
            row.deleteLater()
        self._rows.clear()

    def _append_row(self, kind: str, name: str, value: str) -> None:
        row = QFrame(self.body)
        row.setObjectName("workspace-row")
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN)
        kind_combo = symbol_kind_combo(row, kind)
        name_edit = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, row, name)
        value_edit = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, row, value)
        offsets = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS, "preferences-cancel", row)
        offsets.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.SYMBOL_OFFSETS_ACTION_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT,
        )
        offsets.clicked.connect(lambda: self._open_symbol_offsets(name_edit.text()))
        remove = SymbolRemoveRowButton(row)
        remove.setFixedSize(WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH, WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT)
        remove.clicked.connect(lambda: self._remove_row(row))
        layout.addWidget(kind_combo, 0)
        layout.addWidget(name_edit, 0)
        layout.addWidget(value_edit, 0)
        layout.addWidget(offsets, 0)
        layout.addWidget(remove, 0, Qt.AlignVCenter)
        layout.addStretch(1)
        self._rows.append((kind_combo, name_edit, value_edit, row))
        self.body_layout.addWidget(row, 0)
        self._apply_filter()

    def _open_symbol_offsets(self, name: str) -> None:
        clean_name = name.strip().lstrip("_@")
        offsets = self._symbol_offsets.get(clean_name, [])
        dialog = BinaryWorkbenchSymbolOffsetsDialog(clean_name or name.strip(), offsets, self)
        dialog.goToRequested.connect(self.goToRequested.emit)
        dialog.exec()

    def _remove_row(self, row: QWidget) -> None:
        self._rows = [item for item in self._rows if item[3] is not row]
        row.deleteLater()

    def _apply_filter(self) -> None:
        query = self.filter_input.text().strip().lower()
        for kind, name, value, row in self._rows:
            haystack = f"{kind.currentText()} {name.text()} {value.text()}".lower()
            row.setVisible(not query or query in haystack)
