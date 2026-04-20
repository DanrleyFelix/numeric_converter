from PySide6.QtWidgets import QHBoxLayout, QFrame, QToolButton, QSizePolicy
from PySide6.QtCore import Qt


class Toolbar(QFrame):
    
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 20, 0)
        layout.setSpacing(0)
        self.setObjectName("toolbar")
        self.setFixedHeight(32)

        for text in ("File", "Preferences", "Help"):
            btn = QToolButton()
            btn.setText(text)
            btn.setObjectName(text.lower())
            btn.setMinimumHeight(32)
            btn.setMinimumWidth(120)
            btn.setAutoRaise(True)
            layout.addWidget(btn)

        layout.addStretch()
