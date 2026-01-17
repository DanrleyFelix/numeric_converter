from PySide6.QtWidgets import QFrame, QFormLayout, QLabel, QPlainTextEdit
from PySide6.QtCore import Qt


class ConverterPanel(QFrame):
    def __init__(self):
        super().__init__()

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(20)
        for text in ("Decimal", "Binary", "Hex (BE)", "Hex (LE)"):
            inp = QPlainTextEdit()
            lab = QLabel(text)
            inp.setMinimumHeight(40)
            form.addRow(lab, inp)
            form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

