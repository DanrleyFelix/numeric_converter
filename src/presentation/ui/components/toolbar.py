from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QFrame, QMenu, QToolButton


class Toolbar(QFrame):

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 20, 0)
        layout.setSpacing(0)
        self.setObjectName("toolbar")
        self.setFixedHeight(32)

        self.save_context_action = QAction("Save Context", self)
        self.load_context_action = QAction("Load Context", self)
        self.save_log_action = QAction("Save Log", self)
        self.load_log_action = QAction("Load Log", self)

        self.converter_preferences_action = QAction("Converter Preferences", self)
        self.toggle_key_panel_action = QAction("Show Key Panel", self)
        self.toggle_key_panel_action.setCheckable(True)
        self.toggle_key_panel_action.setChecked(True)

        self.about_action = QAction("About", self)

        file_menu = QMenu(self)
        file_menu.addAction(self.save_context_action)
        file_menu.addAction(self.load_context_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_log_action)
        file_menu.addAction(self.load_log_action)

        preferences_menu = QMenu(self)
        preferences_menu.addAction(self.converter_preferences_action)
        preferences_menu.addSeparator()
        preferences_menu.addAction(self.toggle_key_panel_action)

        help_menu = QMenu(self)
        help_menu.addAction(self.about_action)

        layout.addWidget(self._build_menu_button("File", "file", file_menu))
        layout.addWidget(
            self._build_menu_button("Preferences", "preferences", preferences_menu)
        )
        layout.addWidget(self._build_menu_button("Help", "help", help_menu))
        layout.addStretch()

    def _build_menu_button(self, text: str, object_name: str, menu: QMenu) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setObjectName(object_name)
        button.setMinimumHeight(32)
        button.setMinimumWidth(120)
        button.setAutoRaise(True)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setMenu(menu)
        return button
