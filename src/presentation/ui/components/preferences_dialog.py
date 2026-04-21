from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
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

        self._group_boxes: dict[str, QSpinBox] = {}
        self._zero_pad_boxes: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        title = QLabel("Converter Formatting")
        title.setObjectName("preferences-title")
        layout.addWidget(title)

        grid = QGridLayout()
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
            grid.addWidget(zero_pad, row, 2)

        layout.addLayout(grid)

        self.key_panel_checkbox = QCheckBox("Show Key Panel")
        self.key_panel_checkbox.setChecked(key_panel_visible)
        layout.addWidget(self.key_panel_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
