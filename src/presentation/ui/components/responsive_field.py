from PySide6.QtWidgets import (
    QFrame, QLabel, QPlainTextEdit,
    QVBoxLayout, QHBoxLayout, QSizePolicy)
from PySide6.QtCore import Qt


class ResponsiveField(QFrame):
    
    def __init__(self, text: str, min_h=48, max_h=140):
        super().__init__()

        self.label = QLabel(text)
        self.editor = QPlainTextEdit()

        self.editor.setMinimumHeight(min_h)
        self.editor.setMaximumHeight(max_h)
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._is_vertical = False
        self._set_horizontal()

    def _clear_layout(self):
        lay = self.layout()
        if not lay:
            return
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        lay.deleteLater()

    def _set_horizontal(self):
        self._clear_layout()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        self.label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay.addWidget(self.label)
        lay.addWidget(self.editor, 1)

        self._is_vertical = False

    def _set_vertical(self):
        self._clear_layout()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        lay.addWidget(self.label)
        lay.addWidget(self.editor)

        self._is_vertical = True

    def set_mode(self, vertical: bool):
        if vertical == self._is_vertical:
            return
        self._set_vertical() if vertical else self._set_horizontal()
