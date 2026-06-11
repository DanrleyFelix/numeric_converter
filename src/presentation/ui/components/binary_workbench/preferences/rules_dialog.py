from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QPushButton, QVBoxLayout

from src.modules.dtos import BinaryWorkbenchEditRulesDTO
from src.presentation.ui.components.binary_workbench.preferences.constants import (
    BINARY_WORKBENCH_RULES_LAYOUT,
    BINARY_WORKBENCH_RULES_TEXT,
)


class BinaryWorkbenchRulesDialog(QDialog):
    def __init__(
        self,
        rules: BinaryWorkbenchEditRulesDTO,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_RULES_TEXT.TITLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            BINARY_WORKBENCH_RULES_LAYOUT.MARGIN,
            BINARY_WORKBENCH_RULES_LAYOUT.MARGIN,
            BINARY_WORKBENCH_RULES_LAYOUT.MARGIN,
            BINARY_WORKBENCH_RULES_LAYOUT.MARGIN,
        )
        layout.setSpacing(BINARY_WORKBENCH_RULES_LAYOUT.VERTICAL_SPACING)
        self.insert_shift = self._check(
            BINARY_WORKBENCH_RULES_TEXT.INSERT_SHIFT,
            rules.allow_insert_shift,
        )
        self.append_offsets = self._check(
            BINARY_WORKBENCH_RULES_TEXT.APPEND_OFFSETS,
            rules.allow_append_offsets,
        )
        self.remove_shift = self._check(
            BINARY_WORKBENCH_RULES_TEXT.REMOVE_SHIFT,
            rules.allow_remove_shift,
        )
        self.bytes_edit = self._check(
            BINARY_WORKBENCH_RULES_TEXT.BYTES_EDIT,
            rules.allow_bytes_edit,
        )
        self.assembly_edit = self._check(
            BINARY_WORKBENCH_RULES_TEXT.ASSEMBLY_EDIT,
            rules.allow_assembly_edit,
        )
        for control in (
            self.insert_shift,
            self.append_offsets,
            self.remove_shift,
            self.bytes_edit,
            self.assembly_edit,
        ):
            layout.addWidget(control)
        ok = QPushButton(BINARY_WORKBENCH_RULES_TEXT.CONFIRM, self)
        ok.setObjectName("preferences-confirm")
        ok.setFocusPolicy(Qt.NoFocus)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        layout.addSpacing(BINARY_WORKBENCH_RULES_LAYOUT.CONFIRM_TOP_SPACING)
        layout.addWidget(ok, 0, Qt.AlignCenter)
        self.setFixedSize(self.sizeHint())

    def selected_rules(self) -> BinaryWorkbenchEditRulesDTO:
        return BinaryWorkbenchEditRulesDTO(
            allow_insert_shift=self.insert_shift.isChecked(),
            allow_append_offsets=self.append_offsets.isChecked(),
            allow_remove_shift=self.remove_shift.isChecked(),
            allow_bytes_edit=self.bytes_edit.isChecked(),
            allow_assembly_edit=self.assembly_edit.isChecked(),
        )

    def _check(self, text: str, checked: bool) -> QCheckBox:
        item = QCheckBox(text, self)
        item.setObjectName("binary-workbench-dialog-check")
        item.setChecked(checked)
        item.setCursor(Qt.PointingHandCursor)
        return item
