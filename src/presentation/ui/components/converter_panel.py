from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPlainTextEdit
)
from PySide6.QtCore import Qt


class ConverterPanel(QFrame):
    def __init__(self):
        super().__init__()

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(20)

        for text in ("Decimal", "Binary", "Hex (BE)", "Hex (LE)"):
            row = QHBoxLayout()
            row.setSpacing(20)

            lab = QLabel(text)
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lab.setFixedWidth(90)

            inp = QPlainTextEdit()
            inp.setMinimumHeight(40)

            row.addWidget(lab)
            row.addWidget(inp, 1)

            main.addLayout(row)
