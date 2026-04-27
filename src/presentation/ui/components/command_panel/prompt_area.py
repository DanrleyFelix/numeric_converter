from PySide6.QtCore import QSize
from PySide6.QtWidgets import QWidget


class PromptArea(QWidget):

    def __init__(self, editor: "CommandEdit"):
        super().__init__(editor)
        self.editor = editor
        self.setObjectName("cmd-prompt-area")
        self.setContentsMargins(0, 0, 0, 0)

    def sizeHint(self):
        return QSize(self.editor.promptAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.paintPromptArea(event)
