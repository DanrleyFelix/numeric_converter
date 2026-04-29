from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout

from src.presentation.ui.components.converter_panel.constants import (
    CONVERTER_PANEL_FIELDS,
    CONVERTER_PANEL_LAYOUT,
    CONVERTER_PANEL_TEXT,
)
from src.presentation.ui.components.converter_panel.input_edit import ConverterInputEdit
from src.presentation.ui.design.icons import Icons


class ConverterPanel(QFrame):
    inputEdited = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.inputs: dict[str, ConverterInputEdit] = {}
        self.copy_raw_buttons: dict[str, QToolButton] = {}
        main = QVBoxLayout(self)
        main.setContentsMargins(
            CONVERTER_PANEL_LAYOUT.ROOT_MARGIN,
            CONVERTER_PANEL_LAYOUT.ROOT_MARGIN,
            CONVERTER_PANEL_LAYOUT.ROOT_MARGIN,
            CONVERTER_PANEL_LAYOUT.ROOT_MARGIN,
        )
        main.setSpacing(CONVERTER_PANEL_LAYOUT.ROOT_SPACING)
        for kind, label_text in CONVERTER_PANEL_FIELDS.items():
            row = QHBoxLayout()
            row.setSpacing(CONVERTER_PANEL_LAYOUT.ROW_SPACING)
            label = QLabel(label_text)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setFixedWidth(CONVERTER_PANEL_LAYOUT.LABEL_WIDTH)
            editor = ConverterInputEdit(kind)
            editor.setObjectName(f"converter-{kind}")
            editor.valueEdited.connect(self.inputEdited.emit)
            self.inputs[kind] = editor
            copy_raw = QToolButton()
            copy_raw.setObjectName("copy-raw")
            copy_raw.setIcon(Icons.copy())
            copy_raw.setToolTip(CONVERTER_PANEL_TEXT["copy_raw_tooltip"])
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
