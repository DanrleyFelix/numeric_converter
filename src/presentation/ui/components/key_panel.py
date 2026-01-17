from PySide6.QtWidgets import QFrame, QPushButton, QSizePolicy
from .flow_layout import FlowLayout
from PySide6.QtCore import Qt


class KeyPanel(QFrame):
    def __init__(self):
        super().__init__()

        self.setObjectName("key-panel")
        layout = FlowLayout(self, margin=12, h_spacing=12, v_spacing=12)

        keys = [
            "0", "1", "2", "3", "4", "5", "6", "7",
            "8", "9", "A", "B", "C", "D", "E", "F",
            "+", "-", "x", "÷", "==", "!=", ">=", "<=",
            "=", "&&", "||", "NOT", "&&&&", "|", ">>", "<<",
            "^", "~", "(", ")", "LOG", "CLEAR", "ENTER"
        ]

        for key in keys:
            btn = QPushButton(key)
            if key.lower() in ("log", "clear", "enter"):
                btn.setObjectName(key.lower())

            btn.setMinimumHeight(34)
            btn.setMinimumWidth(56)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setCursor(Qt.PointingHandCursor)

            layout.addWidget(btn)
