from PySide6.QtCore import QRect, QSize, Qt, Signal, QStringListModel
from PySide6.QtGui import QKeyEvent, QPainter, QTextCursor
from PySide6.QtWidgets import (
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.application.dto.command_entry import CommandEntryDTO


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
    submitted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._prompt_text = ">>"
        self._pad_l = 6
        self._pad_r = 2
        self._promptArea = PromptArea(self)

        self._completion_model = QStringListModel(self)
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setFilterMode(Qt.MatchStartsWith)
        self._completer.activated.connect(self.insert_completion)

        popup = QListView()
        popup.setObjectName("command-completer")
        popup.setFocusPolicy(Qt.NoFocus)
        self._completer.setPopup(popup)

        self.setContentsMargins(0, 0, 0, 0)
        self.blockCountChanged.connect(self.updatePromptAreaWidth)
        self.updateRequest.connect(self.updatePromptArea)
        self.updatePromptAreaWidth(0)

    def set_completions(self, values: list[str]) -> None:
        self._completion_model.setStringList(values)

    def promptAreaWidth(self) -> int:
        font_metrics = self.fontMetrics()
        return self._pad_l + font_metrics.horizontalAdvance(self._prompt_text) + self._pad_r

    def updatePromptAreaWidth(self, _=0):
        self.setViewportMargins(self.promptAreaWidth(), 0, 0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        contents_rect = self.contentsRect()
        width = self.promptAreaWidth()
        self._promptArea.setGeometry(
            QRect(contents_rect.left(), contents_rect.top(), width, contents_rect.height())
        )

    def updatePromptArea(self, rect, dy):
        if dy:
            self._promptArea.scroll(0, dy)
        else:
            self._promptArea.update(0, rect.y(), self._promptArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updatePromptAreaWidth()

    def keyPressEvent(self, event: QKeyEvent):
        if self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
                event.ignore()
                return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.submitted.emit()
            event.accept()
            return

        super().keyPressEvent(event)
        self._update_completer()

    def paintPromptArea(self, event):
        painter = QPainter(self._promptArea)
        painter.fillRect(event.rect(), self._promptArea.palette().window())

        font_metrics = self.fontMetrics()
        x_pos = self._pad_l

        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                y_pos = top + (
                    int(self.blockBoundingRect(block).height())
                    + font_metrics.ascent()
                    - font_metrics.descent()
                ) // 2
                painter.drawText(x_pos, y_pos, self._prompt_text)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def insert_completion(self, completion: str) -> None:
        prefix = self.text_under_cursor()
        if not prefix:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(prefix))
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    def text_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText()

    def _update_completer(self) -> None:
        prefix = self.text_under_cursor()
        if not prefix or not (prefix[0].isalpha() or prefix[0] == "_"):
            self._completer.popup().hide()
            return

        if prefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(prefix)
            self._completer.popup().setCurrentIndex(
                self._completer.completionModel().index(0, 0)
            )

        rect = self.cursorRect()
        rect.translate(0, self.fontMetrics().height() + 4)
        rect.setWidth(
            self._completer.popup().sizeHintForColumn(0)
            + self._completer.popup().verticalScrollBar().sizeHint().width()
            + 24
        )
        self._completer.complete(rect)


class CommandPanel(QFrame):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 0, 0, 0)

        title = QLabel("Command Window")
        title.setObjectName("command-title")
        title.setContentsMargins(8, 0, 0, 0)

        self.history_view = QPlainTextEdit()
        self.history_view.setObjectName("command-history")
        self.history_view.setReadOnly(True)
        self.history_view.setPlaceholderText("Command history will appear here.")

        feedback_row = QHBoxLayout()
        feedback_row.setContentsMargins(0, 0, 0, 0)
        feedback_row.setSpacing(10)

        self.feedback = QLabel("Type an expression and press Enter.")
        self.feedback.setObjectName("command-feedback")

        self.convert_toggle = QPushButton("Convert")
        self.convert_toggle.setObjectName("command-convert-toggle")
        self.convert_toggle.setCheckable(True)
        self.convert_toggle.setChecked(False)
        self.convert_toggle.setCursor(Qt.PointingHandCursor)

        feedback_row.addWidget(self.feedback, 1)
        feedback_row.addWidget(self.convert_toggle, 0, Qt.AlignRight)

        self.editor = CommandEdit()
        self.editor.setObjectName("command-editor")
        self.editor.setFixedHeight(88)

        layout.addWidget(title)
        layout.addWidget(self.history_view, 1)
        layout.addLayout(feedback_row)
        layout.addWidget(self.editor)

    def set_input_text(self, value: str) -> None:
        self.editor.setPlainText(value)
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.editor.setTextCursor(cursor)

    def current_input(self) -> str:
        return self.editor.toPlainText()

    def set_completions(self, values: list[str]) -> None:
        self.editor.set_completions(values)

    def convert_enabled(self) -> bool:
        return self.convert_toggle.isChecked()

    def render_history(self, entries: list[CommandEntryDTO]) -> None:
        lines: list[str] = []
        for entry in entries:
            if entry.output:
                lines.append(f"{entry.input} => {entry.output}")
            else:
                lines.append(entry.input)
        self.history_view.setPlainText("\n".join(lines).strip())

    def set_feedback(self, message: str, color: str) -> None:
        self.feedback.setText(message)
        self.feedback.setStyleSheet(f"color: {color};")
