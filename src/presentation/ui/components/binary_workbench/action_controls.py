from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QProxyStyle,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT

BINARY_WORKBENCH_ACTION_OBJECT_NAME = "binary-workbench-action"
BINARY_WORKBENCH_INPUT_OBJECT_NAME = "binary-workbench-input"
_DIALOG_CONTROL_STYLE = None


class _DialogControlStyle(QProxyStyle):
    def subControlRect(self, control, option, sub_control, widget=None):
        rect = super().subControlRect(control, option, sub_control, widget)
        if (
            control == QStyle.ComplexControl.CC_ComboBox
            and sub_control == QStyle.SubControl.SC_ComboBoxEditField
        ):
            margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
            return rect.adjusted(margin, margin, -margin, -margin)
        return rect

    def subElementRect(self, element, option, widget=None):
        rect = super().subElementRect(element, option, widget)
        if element == QStyle.SubElement.SE_PushButtonContents:
            margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
            return rect.adjusted(margin, margin, -margin, -margin)
        return rect


class _DialogComboItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        size = super().sizeHint(option, index)
        return QSize(size.width(), BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.fillRect(option.rect, option.palette.highlight() if selected else option.palette.base())
        painter.setPen(
            option.palette.highlightedText().color()
            if selected
            else option.palette.text().color()
        )
        margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
        text_rect = option.rect.adjusted(margin, 0, -margin, 0)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, str(index.data() or ""))
        painter.restore()


def configure_binary_workbench_action(button: QPushButton) -> None:
    button.setObjectName(BINARY_WORKBENCH_ACTION_OBJECT_NAME)
    button.setFixedSize(
        BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH,
        BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT,
    )
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.NoFocus)


def configure_binary_workbench_dialog_action(button: QPushButton) -> None:
    configure_binary_workbench_action(button)
    configure_binary_workbench_dialog_button(
        button,
        BINARY_WORKBENCH_LAYOUT.SHARED_ACTION_WIDTH,
    )


def configure_binary_workbench_dialog_button(
    button: QPushButton,
    width: int | None = None,
) -> None:
    configure_binary_workbench_control_height(button)
    button.setStyle(_dialog_control_style())
    if width is not None:
        button.setFixedWidth(width)
    button.setCursor(Qt.PointingHandCursor)
    button.setFocusPolicy(Qt.NoFocus)


def configure_binary_workbench_filter(editor: QLineEdit) -> None:
    configure_binary_workbench_input(editor, BINARY_WORKBENCH_LAYOUT.SHARED_FILTER_WIDTH)


def configure_binary_workbench_control_height(widget: QWidget) -> None:
    widget.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
    widget.setContentsMargins(margin, margin, margin, margin)


def configure_binary_workbench_line_edit(
    editor: QLineEdit,
    width: int | None = None,
) -> None:
    editor.setFixedHeight(BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)
    if width is not None:
        editor.setFixedWidth(width)
    margin = BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_CONTENT_MARGIN
    editor.setTextMargins(margin, margin, margin, margin)


def configure_binary_workbench_combo(
    combo: QComboBox,
    width: int | None = None,
) -> None:
    configure_binary_workbench_control_height(combo)
    combo.setStyle(_dialog_control_style())
    combo.setItemDelegate(_DialogComboItemDelegate(combo))
    if width is not None:
        combo.setFixedWidth(width)
    else:
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    combo.setCursor(Qt.PointingHandCursor)


def configure_binary_workbench_input(editor: QLineEdit, width: int) -> None:
    editor.setObjectName(BINARY_WORKBENCH_INPUT_OBJECT_NAME)
    editor.setFixedSize(width, BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)


def _dialog_control_style() -> _DialogControlStyle:
    global _DIALOG_CONTROL_STYLE
    if _DIALOG_CONTROL_STYLE is None:
        _DIALOG_CONTROL_STYLE = _DialogControlStyle()
    return _DIALOG_CONTROL_STYLE
