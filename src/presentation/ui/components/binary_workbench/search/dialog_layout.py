from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


def base_search_dialog_layout(
    dialog: QDialog,
    title_text: str,
    subtitle_text: str,
) -> QVBoxLayout:
    layout = QVBoxLayout(dialog)
    title = QLabel(title_text, dialog)
    title.setObjectName("preferences-title")
    subtitle = QLabel(subtitle_text, dialog)
    subtitle.setObjectName("preferences-subtitle")
    subtitle.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(subtitle)
    return layout


def finish_search_dialog(layout: QVBoxLayout, *widgets) -> None:
    callback = widgets[-1]
    action_button = widgets[-2] if len(widgets) > 1 and isinstance(widgets[-2], QPushButton) else None
    content_widgets = widgets[:-2] if action_button is not None else widgets[:-1]
    for widget in content_widgets:
        layout.addWidget(widget)
    ok = QPushButton("OK")
    ok.setObjectName("preferences-ok")
    ok.setFocusPolicy(Qt.NoFocus)
    ok.setCursor(Qt.PointingHandCursor)
    ok.clicked.connect(callback)
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    if action_button is not None:
        row.addWidget(action_button)
    row.addStretch(1)
    row.addWidget(ok)
    layout.addLayout(row)


def search_line_edit(parent: QDialog, placeholder: str) -> QLineEdit:
    editor = QLineEdit(parent)
    editor.setObjectName("binary-workbench-dialog-input")
    editor.setPlaceholderText(placeholder)
    return editor
