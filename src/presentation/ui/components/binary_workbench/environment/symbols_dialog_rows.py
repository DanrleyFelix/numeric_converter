from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_line_edit,
)
from src.core.binary_workbench.symbol_values import merged_symbol_values
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.environment.symbol_offsets_dialog import (
    BinaryWorkbenchSymbolOffsetsDialog,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    SymbolRemoveRowButton,
    symbol_button,
    symbol_input,
)
from src.presentation.ui.components.binary_workbench.input_validators import set_python_identifier_validator
from src.presentation.ui.components.workspace_table.constants.layout import WORKSPACE_TABLE_SIZE


class SymbolsDialogRowsMixin:
    def values(self) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        symbols: dict[str, str] = {}
        for name, value, _, _ in self._rows:
            if name.text().strip() and value.text().strip():
                symbols[name.text().strip().lstrip("_@")] = value.text().strip()
        return symbols, {}, {}

    def _load_rows(self, variables: dict[str, str], equates: dict[str, str], labels: dict[str, str]) -> None:
        for name, value in merged_symbol_values(None, variables, equates).items():
            self._append_row(str(name), str(value))

    def _merge_rows(self, symbols: dict[str, str]) -> None:
        existing = {
            name.text().strip().lstrip("_@").casefold(): value
            for name, value, _, _ in self._rows
        }
        for name, value in merged_symbol_values(symbols).items():
            key = name.casefold()
            if key in existing:
                existing[key].setText(value)
            else:
                self._append_row(name, value)

    def _append_from_entry(self) -> None:
        self._merge_rows({self.name.text(): self.value.text()})
        self.name.clear()
        self.value.clear()

    def _clear_rows(self) -> None:
        for _, _, row, remove_slot in self._rows:
            row.deleteLater()
            remove_slot.deleteLater()
        self._rows.clear()

    def _append_row(self, name: str, value: str) -> None:
        row = QFrame(self.body)
        row.setObjectName("workspace-row")
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN)
        name_edit = symbol_input(
            BINARY_WORKBENCH_TEXT.SYMBOL_NAME,
            row,
            name,
            expanding=True,
        )
        value_edit = symbol_input(
            BINARY_WORKBENCH_TEXT.SYMBOL_VALUE,
            row,
            value,
            expanding=True,
        )
        configure_binary_workbench_line_edit(name_edit)
        configure_binary_workbench_line_edit(value_edit)
        set_python_identifier_validator(name_edit)
        offsets = symbol_button(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS, "", row)
        configure_binary_workbench_dialog_action(offsets)
        offsets.clicked.connect(lambda: self._open_symbol_offsets(name_edit.text()))
        remove_slot = _remove_slot(self.remove_body)
        remove = SymbolRemoveRowButton(remove_slot)
        remove.setFixedSize(
            WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_WIDTH,
            WORKSPACE_TABLE_SIZE.REMOVE_BUTTON_HEIGHT,
        )
        remove.clicked.connect(lambda: self._remove_row(row, remove_slot))
        layout.addWidget(name_edit, 0, Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(value_edit, 0, Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(offsets, 0, Qt.AlignLeft | Qt.AlignVCenter)
        layout.addStretch(1)
        remove_slot.layout().addWidget(remove, 0, Qt.AlignCenter)
        self._rows.append((name_edit, value_edit, row, remove_slot))
        self.body_layout.addWidget(row, 0)
        self.remove_layout.addWidget(remove_slot, 0)
        self._apply_filter()

    def _open_symbol_offsets(self, name: str) -> None:
        clean_name = name.strip().lstrip("_@")
        offsets = self._symbol_offsets.get(clean_name, [])
        dialog = BinaryWorkbenchSymbolOffsetsDialog(clean_name or name.strip(), offsets, self)
        dialog.goToRequested.connect(self.goToRequested.emit)
        dialog.exec()

    def _remove_row(self, row: QWidget, remove_slot: QWidget) -> None:
        self._rows = [item for item in self._rows if item[2] is not row]
        row.deleteLater()
        remove_slot.deleteLater()

    def _apply_filter(self) -> None:
        query = self.filter_input.text().strip().lower()
        for name, value, row, remove_slot in self._rows:
            haystack = f"{name.text()} {value.text()}".lower()
            visible = not query or query in haystack
            row.setVisible(visible)
            remove_slot.setVisible(visible)


def _remove_slot(parent: QWidget) -> QWidget:
    slot = QWidget(parent)
    slot.setFixedWidth(WORKSPACE_TABLE_SIZE.REMOVE_GUTTER_WIDTH)
    slot.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    layout = QVBoxLayout(slot)
    layout.setContentsMargins(*ENVIRONMENT_LAYOUT.EMPTY_MARGINS)
    return slot
