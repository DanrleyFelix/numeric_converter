from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from src.application.dto.formatting_context import FormattingOutputDTO


class PreferencesDialog(QDialog):

    def __init__(
        self,
        formatting: dict[str, FormattingOutputDTO],
        key_panel_visible: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.setMinimumSize(620, 430)

        self._group_boxes: dict[str, QSpinBox] = {}
        self._zero_pad_boxes: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("Preferences")
        title.setObjectName("preferences-title")
        layout.addWidget(title)

        subtitle = QLabel("Configure grouping, zero padding and visibility options.")
        subtitle.setObjectName("preferences-subtitle")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        grid.addWidget(QLabel("Field"), 0, 0)
        grid.addWidget(QLabel("Group Size"), 0, 1)
        grid.addWidget(QLabel("Zero Pad"), 0, 2)

        labels = {
            "decimal": "Decimal",
            "binary": "Binary",
            "hexBE": "Hex (BE)",
            "hexLE": "Hex (LE)",
        }

        for row, (key, label_text) in enumerate(labels.items(), start=1):
            group_size = QSpinBox()
            group_size.setRange(0, 64)
            group_size.setValue(formatting[key].group_size)

            zero_pad = QCheckBox()
            zero_pad.setChecked(formatting[key].zero_pad)
            zero_pad.setLayoutDirection(Qt.LeftToRight)

            self._group_boxes[key] = group_size
            self._zero_pad_boxes[key] = zero_pad

            grid.addWidget(QLabel(label_text), row, 0)
            grid.addWidget(group_size, row, 1)
            grid.addWidget(zero_pad, row, 2, Qt.AlignLeft)

        layout.addLayout(grid)

        self.key_panel_checkbox = QCheckBox("Show Key Panel")
        self.key_panel_checkbox.setChecked(key_panel_visible)
        self.key_panel_checkbox.setObjectName("preferences-key-panel")
        layout.addWidget(self.key_panel_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        if buttons.layout() is not None:
            buttons.layout().setSpacing(12)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        cancel_button = buttons.button(QDialogButtonBox.Cancel)

        for button in (ok_button, cancel_button):
            if isinstance(button, QPushButton):
                button.setMinimumWidth(140)
                button.setMinimumHeight(38)

        if isinstance(ok_button, QPushButton):
            ok_button.setObjectName("preferences-ok")
        if isinstance(cancel_button, QPushButton):
            cancel_button.setObjectName("preferences-cancel")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_formatting(self) -> dict[str, FormattingOutputDTO]:
        return {
            key: FormattingOutputDTO(
                group_size=self._group_boxes[key].value(),
                zero_pad=self._zero_pad_boxes[key].isChecked(),
            )
            for key in self._group_boxes
        }

    def key_panel_visible(self) -> bool:
        return self.key_panel_checkbox.isChecked()
