from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPlainTextEdit)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QTextOption

from src.presentation.ui.design.metrics import Metrics


CONVERTER_LABELS = [
        "Decimal",
        "Binary",
        "Hexadecimal (Big Endian)",
        "Hexadecimal (Litle Endian)"]
    

def define_converter_labels(layout: QVBoxLayout):

    for key in CONVERTER_LABELS:
        subtitle = QLabel(key)
        layout.addWidget(subtitle)
        input = QLineEdit()
        input.setObjectName("ConverterInput")
        input.setMinimumHeight(Metrics.INPUT_MIN_H)
        input.setMinimumWidth(Metrics.INPUT_MIN_W)
        input.setMaximumWidth(Metrics.INPUT_MAX_W)
        layout.addWidget(input)
        subtitle.setObjectName("Subtitle")

class BaseConverterWidget(QWidget):

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.setAttribute(Qt.WA_StyledBackground, True)


        title = QLabel("</> Converter")
        title.setObjectName("WidgetTitle") 
        layout.addWidget(title)

        define_converter_labels(layout)

        layout.addStretch()


class ExpressionWidget(QWidget):

    submit_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        title = QLabel("⚙️ Command Window")
        title.setObjectName("WidgetTitle")
        layout.addWidget(title)

        label_input_cmd = QLabel("Type your expression:")
        layout.addWidget(label_input_cmd)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(">>")
        self.input.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.input.setTabChangesFocus(False)
        self.input.setObjectName("ExpressionInput")

        self.input.keyPressEvent = self._on_key_press

        layout.addWidget(self.input)
        layout.addStretch()

    def _on_key_press(self, event):
        if event.key() == Qt.Key_Return and not event.modifiers():
            self.submit_requested.emit()
        else:
            QPlainTextEdit.keyPressEvent(self.input, event)


class VirtualKeyboardWidget(QWidget):

    key_pressed = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("[Virtual Keyboard Placeholder]"))
        layout.addStretch()


class LogPanelWidget(QWidget):

    clear_log_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        title = QLabel("Logs")
        title.setObjectName("WidgetTitleLog")
        layout.addWidget(title)

        layout.addStretch()


