from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT


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
    button_width: int | None = None,
    confirm_object_name: str = "preferences-ok",
    center_confirm: bool = False,
    spread_actions: bool = False,
) -> QPushButton:
    callback = widgets[-1]
    action_button = widgets[-2] if len(widgets) > 1 and isinstance(widgets[-2], QPushButton) else None
    content_widgets = widgets[:-2] if action_button is not None else widgets[:-1]
    for widget in content_widgets:
        layout.addWidget(widget)
    ok = QPushButton(confirm_text)
    ok.setObjectName(confirm_object_name)
    ok.setFocusPolicy(Qt.NoFocus)
    ok.setCursor(Qt.PointingHandCursor)
    if button_width is not None:
        ok.setFixedWidth(button_width)
        ok.setProperty("compactSearch", True)
        if action_button is not None:
            action_button.setFixedWidth(button_width)
            action_button.setProperty("compactSearch", True)
    ok.clicked.connect(callback)
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    if action_button is not None and spread_actions:
        row.addWidget(action_button)
        row.addStretch(1)
        row.addWidget(ok)
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
    return editor


def configure_search_combo_popup(combo: QComboBox) -> None:
    view = combo.view()
    view.setViewportMargins(BINARY_WORKBENCH_LAYOUT.SEARCH_COMBO_OPTION_LEFT_MARGIN, 0, 0, 0)
    view.setSpacing(BINARY_WORKBENCH_LAYOUT.SEARCH_COMBO_OPTION_SPACING)
