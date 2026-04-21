from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu, QToolButton

from src.presentation.ui.design.icons import Icons


class Toolbar(QFrame):

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(0)
        self.setObjectName("toolbar")
        self.setFixedHeight(40)

        self.save_context_action = QAction("Save Context", self)
        self.load_context_action = QAction("Load Context", self)
        self.save_log_action = QAction("Save Log", self)
        self.load_log_action = QAction("Load Log", self)

        self.converter_preferences_action = QAction("Converter", self)
        self.toggle_key_panel_action = QAction("Show Key Panel", self)
        self.toggle_key_panel_action.setCheckable(True)
        self.toggle_key_panel_action.setChecked(True)

        file_menu = QMenu(self)
        file_menu.addAction(self.save_context_action)
        file_menu.addAction(self.load_context_action)
        file_menu.addAction(self.save_log_action)
        file_menu.addAction(self.load_log_action)

        preferences_menu = QMenu(self)
        preferences_menu.addAction(self.converter_preferences_action)
        preferences_menu.addAction(self.toggle_key_panel_action)

        self.file_button = self._build_menu_button("File", "file", Icons.file(), file_menu)
        self.preferences_button = self._build_menu_button(
            "Preferences",
            "preferences",
            Icons.preferences(),
            preferences_menu,
        )
        self.help_button = self._build_action_button("Help", "help", Icons.help())

        layout.addWidget(self.file_button)
        layout.addWidget(self.preferences_button)
        layout.addWidget(self.help_button)
        layout.addStretch()

    def _build_menu_button(
        self,
        text: str,
        object_name: str,
        icon,
        menu: QMenu,
    ) -> QToolButton:
        button = self._build_base_button(text, object_name, icon)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setMenu(menu)
        return button

    def _build_action_button(self, text: str, object_name: str, icon) -> QToolButton:
        return self._build_base_button(text, object_name, icon)

    def _build_base_button(self, text: str, object_name: str, icon) -> QToolButton:
        button = QToolButton()
        button.setText(f"  {text}")
        button.setIcon(icon)
        button.setIconSize(QSize(16, 16))
        button.setObjectName(object_name)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setMinimumHeight(40)
        button.setMinimumWidth(126)
        button.setAutoRaise(True)
        button.setCursor(Qt.PointingHandCursor)
        return button
