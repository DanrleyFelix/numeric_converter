from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
)

from src.presentation.ui.components.binary_workbench.action_controls import (
    configure_binary_workbench_combo,
    configure_binary_workbench_dialog_action,
    configure_binary_workbench_line_edit,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT


class SearchComboOptionDelegate(QStyledItemDelegate):
    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        size = super().sizeHint(option, index)
        return QSize(size.width(), BINARY_WORKBENCH_LAYOUT.SHARED_CONTROL_HEIGHT)

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setFont(option.font)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.fillRect(option.rect, option.palette.base())
            painter.setPen(option.palette.text().color())
        text_rect = option.rect.adjusted(
            BINARY_WORKBENCH_LAYOUT.SEARCH_COMBO_OPTION_TEXT_MARGIN,
            BINARY_WORKBENCH_LAYOUT.SEARCH_COMBO_OPTION_TEXT_MARGIN,
            -BINARY_WORKBENCH_LAYOUT.SEARCH_COMBO_OPTION_TEXT_MARGIN,
            -BINARY_WORKBENCH_LAYOUT.SEARCH_COMBO_OPTION_TEXT_MARGIN,
        )
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, str(index.data() or ""))
        painter.restore()


def base_search_dialog_layout(
    dialog: QDialog,
    title_text: str,
    subtitle_text: str,
    *,
    include_header: bool = True,
    spacing: int = BINARY_WORKBENCH_LAYOUT.SEARCH_DIALOG_SPACING,
    margins: int | tuple[int, int] = BINARY_WORKBENCH_LAYOUT.SEARCH_DIALOG_MARGIN,
) -> QVBoxLayout:
    layout = QVBoxLayout(dialog)
    if isinstance(margins, tuple):
        vertical, horizontal = margins
        layout.setContentsMargins(horizontal, vertical, horizontal, vertical)
    else:
        layout.setContentsMargins(margins, margins, margins, margins)
    layout.setSpacing(spacing)
    if not include_header:
        return layout
    title = QLabel(title_text, dialog)
    title.setObjectName("preferences-title")
    subtitle = QLabel(subtitle_text, dialog)
    subtitle.setObjectName("preferences-subtitle")
    subtitle.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(subtitle)
    return layout


def finish_search_dialog(
    layout: QVBoxLayout,
    *widgets,
    confirm_text: str = "OK",
    center_confirm: bool = False,
    spread_actions: bool = False,
) -> QPushButton:
    callback = widgets[-1]
    action_button = widgets[-2] if len(widgets) > 1 and isinstance(widgets[-2], QPushButton) else None
    content_widgets = widgets[:-2] if action_button is not None else widgets[:-1]
    for widget in content_widgets:
        layout.addWidget(widget)
    ok = QPushButton(confirm_text)
    configure_binary_workbench_dialog_action(ok)
    if action_button is not None:
        configure_binary_workbench_dialog_action(action_button)
    ok.clicked.connect(callback)
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    if action_button is not None and spread_actions:
        row.addWidget(action_button, 0, Qt.AlignLeft)
        row.addStretch(1)
        row.addWidget(ok, 0, Qt.AlignRight)
    elif action_button is not None:
        row.addWidget(action_button)
        row.addSpacing(BINARY_WORKBENCH_LAYOUT.SYMBOL_ROW_SIDE_MARGIN)
        row.addWidget(ok)
        row.addStretch(1)
    elif center_confirm:
        row.addStretch(1)
        row.addWidget(ok)
        row.addStretch(1)
    else:
        row.addStretch(1)
        row.addWidget(ok)
    layout.addLayout(row)
    return ok


def search_line_edit(parent: QDialog, placeholder: str) -> QLineEdit:
    editor = QLineEdit(parent)
    editor.setObjectName("binary-workbench-dialog-input")
    editor.setPlaceholderText(placeholder)
    configure_binary_workbench_line_edit(editor)
    return editor


def configure_search_combo_popup(combo: QComboBox) -> None:
    configure_binary_workbench_combo(combo)
    view = combo.view()
    view.setViewportMargins(0, 0, 0, 0)
    view.setSpacing(BINARY_WORKBENCH_LAYOUT.SEARCH_COMBO_OPTION_SPACING)
    view.setItemDelegate(SearchComboOptionDelegate(view))
