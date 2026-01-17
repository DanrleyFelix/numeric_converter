from PySide6.QtWidgets import QVBoxLayout, QLabel, QPlainTextEdit, QFrame


class CommandPanel(QFrame):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Command Window")
        title.setObjectName("command-title")

        editor = QPlainTextEdit()
        editor.setObjectName("command-editor")

        layout.addWidget(title)
        layout.addWidget(editor, 1)
