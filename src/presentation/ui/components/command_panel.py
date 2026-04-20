from PySide6.QtWidgets import QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPlainTextEdit, QWidget


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


class CommandEdit(QPlainTextEdit):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._prompt_text = ">>"
        self._pad_l = 6
        self._pad_r = 2

        self._promptArea = PromptArea(self)
        self.setContentsMargins(0, 0, 0, 0)

        self.blockCountChanged.connect(self.updatePromptAreaWidth)
        self.updateRequest.connect(self.updatePromptArea)

        self.updatePromptAreaWidth(0)

    def promptAreaWidth(self) -> int:
        fm = self.fontMetrics()
        return self._pad_l + fm.horizontalAdvance(self._prompt_text) + self._pad_r

    def updatePromptAreaWidth(self, _=0):
        self.setViewportMargins(self.promptAreaWidth(), 0, 0, 0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        w = self.promptAreaWidth()
        self._promptArea.setGeometry(QRect(cr.left(), cr.top(), w, cr.height()))

    def updatePromptArea(self, rect, dy):
        if dy:
            self._promptArea.scroll(0, dy)
        else:
            self._promptArea.update(0, rect.y(), self._promptArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updatePromptAreaWidth()

    def paintPromptArea(self, event):
        painter = QPainter(self._promptArea)
        painter.fillRect(event.rect(), self._promptArea.palette().window())

        fm = self.fontMetrics()
        x = self._pad_l

        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                y = top + (int(self.blockBoundingRect(block).height()) + fm.ascent() - fm.descent()) // 2
                painter.drawText(x, y, self._prompt_text)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())


class CommandPanel(QFrame):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 0, 0, 0)

        title = QLabel("Command Window")
        title.setObjectName("command-title")
        title.setContentsMargins(8, 0, 0, 0)

        editor = CommandEdit()
        editor.setObjectName("command-editor")

        layout.addWidget(title)
        layout.addWidget(editor, 1)
