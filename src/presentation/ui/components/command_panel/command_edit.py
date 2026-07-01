from PySide6.QtCore import QEvent, QItemSelectionModel, QRect, Qt, Signal, QStringListModel
from PySide6.QtGui import QKeyEvent, QPainter, QTextCursor
from PySide6.QtWidgets import QCompleter, QFrame, QListView, QPlainTextEdit

from src.presentation.ui.components.command_panel.prompt_area import PromptArea
from src.presentation.ui.helpers.completer_popup import fit_completer_popup_height
from src.presentation.ui.helpers.load_qss import STYLESHEET


class CommandEdit(QPlainTextEdit):
    submitted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._prompt_text = ">>"
        self._pad_l = 6
        self._pad_r = 2
        self._history_entries: list[str] = []
        self._variable_completions: list[str] = []
        self._history_mode_active = False
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
        popup.setStyleSheet(STYLESHEET)
        popup.setFocusPolicy(Qt.NoFocus)
        popup.setFrameShape(QFrame.NoFrame)
        popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        popup.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        popup.setUniformItemSizes(True)
        popup.setMouseTracking(True)
        popup.setSpacing(0)
        popup.installEventFilter(self)
        self._completer.setPopup(popup)
        self.setContentsMargins(0, 0, 0, 0)
        self.blockCountChanged.connect(self.updatePromptAreaWidth)
        self.updateRequest.connect(self.updatePromptArea)
        self.updatePromptAreaWidth(0)
        self.setTabChangesFocus(False)

    def set_completions(self, values: list[str]) -> None:
        self._variable_completions = list(values)
        if not self._history_mode_active:
            self._completion_model.setStringList(values)

    def set_history_entries(self, values: list[str]) -> None:
        self._history_entries = list(values)

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
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                self._move_popup_selection(-1 if event.key() == Qt.Key_Up else 1)
                event.accept()
                return
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                self._accept_popup_completion()
                event.accept()
                return
            if event.key() in (Qt.Key_Escape, Qt.Key_Backtab):
                if event.key() == Qt.Key_Escape:
                    self._hide_history_popup()
                event.accept()
                return
        elif event.key() == Qt.Key_Up:
            self._show_history_popup()
            event.accept()
            return
        elif event.key() == Qt.Key_Down:
            event.accept()
            return

        if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            event.accept()
            return

        if self._history_mode_active:
            self._hide_history_popup()
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)
        self._update_completer()

    def eventFilter(self, watched, event) -> bool:
        popup = self._completer.popup()
        if watched is popup and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                self._move_popup_selection(-1 if event.key() == Qt.Key_Up else 1)
                event.accept()
                return True
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                self._accept_popup_completion()
                event.accept()
                return True
            if event.key() == Qt.Key_Escape:
                if self._history_mode_active:
                    self._hide_history_popup()
                else:
                    popup.hide()
                event.accept()
                return True
        return super().eventFilter(watched, event)

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
        if self._history_mode_active:
            self.setPlainText(completion)
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)
            self._hide_history_popup()
            return
        prefix = self.text_under_cursor()
        if not prefix:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(prefix))
        cursor.insertText(completion)
        self.setTextCursor(cursor)
        self._completer.popup().hide()

    def text_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText()

    def _update_completer(self) -> None:
        if self._history_mode_active:
            return
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
            + 24
        )
        self._completer.complete(rect)
        fit_completer_popup_height(self._completer)

    def _show_history_popup(self) -> None:
        entries = [entry for entry in reversed(self._history_entries) if entry]
        if not entries:
            return
        self._history_mode_active = True
        self._completion_model.setStringList(entries)
        self._completer.setCompletionPrefix("")
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completion_model.index(0, 0))
        rect = self.cursorRect()
        rect.translate(0, self.fontMetrics().height() + 4)
        rect.setWidth(
            popup.sizeHintForColumn(0)
            + 24
        )
        self._completer.complete(rect)
        fit_completer_popup_height(self._completer)

    def _move_popup_selection(self, step: int) -> None:
        popup = self._completer.popup()
        current = popup.currentIndex().row()
        model = popup.model()
        count = model.rowCount()
        if count <= 0:
            return
        if current < 0:
            target = count - 1 if step < 0 else 0
        else:
            target = (current + step) % count
        index = model.index(target, 0)
        popup.setCurrentIndex(index)
        popup.selectionModel().setCurrentIndex(index, QItemSelectionModel.ClearAndSelect)

    def _accept_popup_completion(self) -> None:
        completion = self._completer.popup().currentIndex().data()
        if completion:
            self.insert_completion(str(completion))

    def _hide_history_popup(self) -> None:
        if not self._history_mode_active:
            return
        self._history_mode_active = False
        self._completion_model.setStringList(self._variable_completions)
        self._completer.popup().hide()
