from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QDialog,
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

        subtitle = QLabel("Configure grouping and zero padding for each converter input.")
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

            self._group_boxes[key] = group_size
            self._zero_pad_boxes[key] = zero_pad

            grid.addWidget(QLabel(label_text), row, 0)
            grid.addWidget(group_size, row, 1)
            grid.addWidget(zero_pad, row, 2, Qt.AlignLeft)

        layout.addLayout(grid)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 12, 0, 0)
        buttons_row.setSpacing(12)

        cancel_button = QPushButton("Cancel")
        ok_button = QPushButton("OK")

        for button in (ok_button, cancel_button):
            button.setMinimumWidth(160)
            button.setMinimumHeight(38)

        ok_button.setObjectName("preferences-ok")
        cancel_button.setObjectName("preferences-cancel")

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        buttons_row.addWidget(cancel_button, 0, Qt.AlignLeft)
        buttons_row.addStretch(1)
        buttons_row.addWidget(ok_button, 0, Qt.AlignRight)
        layout.addLayout(buttons_row)

    def selected_formatting(self) -> dict[str, FormattingOutputDTO]:
        return {
            key: FormattingOutputDTO(
                group_size=self._group_boxes[key].value(),
                zero_pad=self._zero_pad_boxes[key].isChecked(),
            )
            for key in self._group_boxes
        }
