from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QPushButton, QVBoxLayout

from src.modules.binary_workbench_dtos import BinaryWorkbenchEditRulesDTO
from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_action,
    configure_binary_workbench_control_height,
)
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
        self.byte_shift = self._check(
            BINARY_WORKBENCH_RULES_TEXT.BYTE_SHIFT,
            rules.allow_byte_shift,
        )
        self.editor_edit = self._check(
            BINARY_WORKBENCH_RULES_TEXT.EDITOR_EDIT,
            rules.allow_editor_edit,
        )
        self.free_after_end = self._check(
            BINARY_WORKBENCH_RULES_TEXT.FREE_AFTER_END,
            rules.allow_free_edit_after_original_end,
        )
        for control in (
            self.byte_shift,
            self.editor_edit,
            self.free_after_end,
        ):
            layout.addWidget(control)
        ok = QPushButton(BINARY_WORKBENCH_RULES_TEXT.CONFIRM, self)
        configure_binary_workbench_action(ok)
        ok.clicked.connect(self.accept)
        layout.addSpacing(BINARY_WORKBENCH_RULES_LAYOUT.CONFIRM_TOP_SPACING)
        layout.addWidget(ok, 0, Qt.AlignCenter)
        self.setFixedSize(self.sizeHint())

    def selected_rules(self) -> BinaryWorkbenchEditRulesDTO:
        return BinaryWorkbenchEditRulesDTO(
            allow_byte_shift=self.byte_shift.isChecked(),
            allow_editor_edit=self.editor_edit.isChecked(),
            allow_free_edit_after_original_end=self.free_after_end.isChecked(),
        )

    def _check(self, text: str, checked: bool) -> QCheckBox:
        item = QCheckBox(text, self)
        item.setObjectName("binary-workbench-dialog-check")
        item.setChecked(checked)
        item.setCursor(Qt.PointingHandCursor)
        configure_binary_workbench_control_height(item)
        return item
