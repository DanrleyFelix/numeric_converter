from PySide6.QtWidgets import QLineEdit


class InputField(QLineEdit):

    def __init__(self, placeholder: str):
        super().__init__()
        self.setPlaceholderText(placeholder)