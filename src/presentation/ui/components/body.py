from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from src.presentation.ui.components.command_panel import CommandPanel
from src.presentation.ui.components.converter_panel import ConverterPanel
from src.presentation.ui.components.body_constants import BODY_FOCUS_ORDER, BODY_LAYOUT


class Body(QFrame):

    def __init__(self):
        super().__init__()
        self.converter_panel = ConverterPanel()
        self.command_panel = CommandPanel()

        layout = QHBoxLayout(self)
        self.setObjectName("body")
        layout.setSpacing(BODY_LAYOUT.SPACING)
        layout.setContentsMargins(
            BODY_LAYOUT.MARGIN,
            BODY_LAYOUT.MARGIN,
            BODY_LAYOUT.MARGIN,
            BODY_LAYOUT.MARGIN,
        )

        layout.addWidget(self.converter_panel, 1)
        layout.addWidget(self.command_panel, 1)
        self._focus_targets: dict[str, QWidget] = {
            **self.converter_panel.inputs,
            "command": self.command_panel.editor,
        }
        for widget in self._focus_targets.values():
            widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if (
            event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and watched in self._focus_targets.values()
        ):
            if event.key() == Qt.Key_Tab:
                self.focus_next()
                event.accept()
                return True
            if event.key() == Qt.Key_Backtab:
                self.focus_previous()
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def focus_decimal(self) -> None:
        self._focus_target("decimal")

    def focus_binary(self) -> None:
        self._focus_target("binary")

    def focus_hex_be(self) -> None:
        self._focus_target("hexBE")

    def focus_hex_le(self) -> None:
        self._focus_target("hexLE")

    def focus_command(self) -> None:
        self._focus_target("command")

    def focus_next(self) -> None:
        self._focus_relative(1)

    def focus_previous(self) -> None:
        self._focus_relative(-1)

    def _focus_relative(self, step: int) -> None:
        active = next(
            (
                key
                for key, widget in self._focus_targets.items()
                if widget.hasFocus()
            ),
            BODY_FOCUS_ORDER[0],
        )
        index = BODY_FOCUS_ORDER.index(active)
        self._focus_target(BODY_FOCUS_ORDER[(index + step) % len(BODY_FOCUS_ORDER)])

    def _focus_target(self, key: str) -> None:
        widget = self._focus_targets[key]
        widget.setFocus(Qt.ShortcutFocusReason)
        cursor = getattr(widget, "textCursor", None)
        set_cursor = getattr(widget, "setTextCursor", None)
        if callable(cursor) and callable(set_cursor):
            text_cursor = cursor()
            text_cursor.movePosition(QTextCursor.End)
            set_cursor(text_cursor)
