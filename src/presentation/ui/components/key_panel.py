from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QPushButton, QSizePolicy

from .flow_layout import FlowLayout


class KeyPanel(QFrame):
    keyPressed = Signal(str)

    def __init__(self):
        super().__init__()

        self.setObjectName("key-panel")
        self.buttons: dict[str, QPushButton] = {}
        layout = FlowLayout(self, margin=12, h_spacing=12, v_spacing=12)

        keys = [
            "0", "1", "2", "3", "4", "5", "6", "7",
            "8", "9", "A", "B", "C", "D", "E", "F",
            "+", "-", "x", "÷", "^", "==", "!=", ">=", "<=",
            "=", "&", "|", "~", "NOT", "OR", "AND", "XOR", ">>", "<<",
            "(", ")", "0x", "0b",
            "LOG", "CLEAR", "ENTER",
        ]

        for key in keys:
            button = QPushButton(key)
            if key.lower() in ("log", "clear", "enter"):
                button.setObjectName(key.lower())

            button.setMinimumHeight(34)
            button.setMinimumWidth(56)
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _, key=key: self.keyPressed.emit(key))

            self.buttons[key] = button
            layout.addWidget(button)
