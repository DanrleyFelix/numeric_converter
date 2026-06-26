from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_control_height,
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.preferences.constants import (
    BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT,
)

class BinaryWorkbenchReferenceOffsetsDialog(QDialog):
    def __init__(
        self,
        reference_offsets: list[str],
        reference_offset_bases: dict[str, str],
        visible_columns: dict[str, bool],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.REFERENCE_OFFSETS)
        self.setFixedWidth(BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.DIALOG_WIDTH)
        self.setMaximumHeight(
            BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.DIALOG_MAX_HEIGHT
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            *(BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.MARGIN,) * 4
        )
        layout.setSpacing(BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.LAYOUT_SPACING)
        self._rows: list[tuple[QLineEdit, QLineEdit, QCheckBox]] = []
        names = [value for value in reference_offsets if value != "File"]
        for name in names[: BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.MAX_ROWS]:
            self._append_row(layout, name, reference_offset_bases.get(name, "0x00000000"), visible_columns.get(name, True))
        missing_rows = BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.MAX_ROWS - len(self._rows)
        for _ in range(missing_rows):
            self._append_row(layout, "", "0x00000000", False)
        ok = QPushButton(BINARY_WORKBENCH_TEXT.CONFIRM, self)
        configure_binary_workbench_dialog_action(ok)
        ok.clicked.connect(self.accept)
        layout.addSpacing(BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.CONFIRM_TOP_SPACING)
        layout.addWidget(ok, 0, Qt.AlignCenter)

    def values(self) -> tuple[list[str], dict[str, str], dict[str, bool]]:
        offsets = ["File"]
        bases = {"File": "0x00000000"}
        visible = {"File": True}
        for name_field, base_field, visible_box in self._rows:
            name = name_field.text().strip()
            if not name:
                continue
            offsets.append(name)
            bases[name] = base_field.text().strip() or "0x00000000"
            visible[name] = visible_box.isChecked()
        return offsets, bases, visible

    def _append_row(
        self,
        parent_layout: QVBoxLayout,
        name: str,
        base: str,
        visible: bool,
    ) -> None:
        row = QHBoxLayout()
        row.setSpacing(
            BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.HORIZONTAL_SPACING
        )
        name_field = QLineEdit(name, self)
        name_field.setObjectName("binary-workbench-dialog-input")
        name_field.setPlaceholderText(BINARY_WORKBENCH_TEXT.REFERENCE_NAME)
        configure_binary_workbench_line_edit(
            name_field,
            BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.CONTROL_WIDTH,
        )
        base_field = QLineEdit(base, self)
        base_field.setObjectName("binary-workbench-dialog-input")
        base_field.setPlaceholderText(BINARY_WORKBENCH_TEXT.REFERENCE_BASE)
        configure_binary_workbench_line_edit(
            base_field,
            BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.CONTROL_WIDTH,
        )
        visible_box = QCheckBox(BINARY_WORKBENCH_TEXT.REFERENCE_VISIBLE, self)
        visible_box.setChecked(visible)
        visible_box.setCursor(Qt.PointingHandCursor)
        configure_binary_workbench_control_height(visible_box)
        row.addWidget(name_field, 2)
        row.addWidget(base_field, 2)
        row.addWidget(visible_box, 1)
        if self._rows:
            parent_layout.addSpacing(
                BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT.IDENTICAL_ITEM_SPACING
            )
        self._rows.append((name_field, base_field, visible_box))
        parent_layout.addLayout(row)
