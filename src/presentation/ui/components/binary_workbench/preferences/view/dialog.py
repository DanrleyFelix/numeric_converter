from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_action,
    configure_binary_workbench_dialog_button,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)


class BinaryWorkbenchViewDialog(QDialog):
    def __init__(self, reference_offsets: list[str], visible_columns: dict[str, bool], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.VIEW)
        self.setFixedSize(BINARY_WORKBENCH_LAYOUT.VIEW_DIALOG_WIDTH, BINARY_WORKBENCH_LAYOUT.VIEW_DIALOG_HEIGHT)
        self._offset_names = reference_offsets or [BINARY_WORKBENCH_TEXT.FILE]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(BINARY_WORKBENCH_LAYOUT.VIEW_DIALOG_MARGIN,) * 4)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.VIEW_DIALOG_GAP)
        self._buttons = {
            BINARY_WORKBENCH_TEXT.BYTES: self._toggle(BINARY_WORKBENCH_TEXT.BYTES, visible_columns.get(BINARY_WORKBENCH_TEXT.BYTES, True)),
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: self._toggle(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, visible_columns.get(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, True)),
            BINARY_WORKBENCH_TEXT.DECODED_TEXT: self._toggle(BINARY_WORKBENCH_TEXT.DECODED_TEXT, visible_columns.get(BINARY_WORKBENCH_TEXT.DECODED_TEXT, False)),
            BINARY_WORKBENCH_TEXT.OFFSETS: self._toggle(BINARY_WORKBENCH_TEXT.OFFSETS, all(visible_columns.get(name, True) for name in self._offset_names)),
        }
        for button in self._buttons.values():
            layout.addWidget(button, 0, Qt.AlignHCenter)
        layout.addStretch(1)
        confirm = QPushButton(BINARY_WORKBENCH_TEXT.CONFIRM, self)
        configure_binary_workbench_action(confirm)
        confirm.clicked.connect(self.accept)
        layout.addWidget(confirm, 0, Qt.AlignHCenter)

    def visible_columns(self) -> dict[str, bool]:
        values = {
            BINARY_WORKBENCH_TEXT.INSTRUCTION: True,
            BINARY_WORKBENCH_TEXT.BYTES: self._buttons[BINARY_WORKBENCH_TEXT.BYTES].isChecked(),
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: self._buttons[BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS].isChecked(),
            BINARY_WORKBENCH_TEXT.DECODED_TEXT: self._buttons[BINARY_WORKBENCH_TEXT.DECODED_TEXT].isChecked(),
        }
        offsets_visible = self._buttons[BINARY_WORKBENCH_TEXT.OFFSETS].isChecked()
        values.update({name: offsets_visible for name in self._offset_names})
        return values

    def _toggle(self, text: str, checked: bool) -> QPushButton:
        button = QPushButton(text, self)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.VIEW_BUTTON_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT,
        )
        configure_binary_workbench_dialog_button(button)
        button.clicked.connect(lambda: self._sync_style(button))
        self._sync_style(button)
        return button

    def _sync_style(self, button: QPushButton) -> None:
        button.setObjectName("binary-workbench-version-active" if button.isChecked() else "binary-workbench-version-item")
        button.style().unpolish(button)
        button.style().polish(button)
