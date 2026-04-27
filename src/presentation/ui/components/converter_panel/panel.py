from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout

from src.presentation.ui.components.converter_panel.input_edit import ConverterInputEdit
from src.presentation.ui.design.icons import Icons


class ConverterPanel(QFrame):
    inputEdited = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.inputs: dict[str, ConverterInputEdit] = {}
        self.copy_raw_buttons: dict[str, QToolButton] = {}
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(20)
        for kind, label_text in {
            "decimal": "Decimal",
            "binary": "Binary",
            "hexBE": "Hex (BE)",
            "hexLE": "Hex (LE)",
        }.items():
            row = QHBoxLayout()
            row.setSpacing(10)
            label = QLabel(label_text)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setFixedWidth(90)
            editor = ConverterInputEdit(kind)
            editor.setObjectName(f"converter-{kind}")
            editor.valueEdited.connect(self.inputEdited.emit)
            self.inputs[kind] = editor
            copy_raw = QToolButton()
            copy_raw.setObjectName("copy-raw")
            copy_raw.setIcon(Icons.copy())
            copy_raw.setToolTip("Copy raw")
            copy_raw.setCursor(Qt.PointingHandCursor)
            copy_raw.clicked.connect(editor.copy_raw_to_clipboard)
            self.copy_raw_buttons[kind] = copy_raw
            row.addWidget(label)
            row.addWidget(editor, 1)
            row.addWidget(copy_raw)
            main.addLayout(row)

    def set_values(self, raw_values: dict[str, str], display_values: dict[str, str]) -> None:
        for key, editor in self.inputs.items():
            editor.set_content(raw_values.get(key, ""), display_values.get(key, ""))
