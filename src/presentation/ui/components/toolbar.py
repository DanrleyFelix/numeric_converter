from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu, QToolButton

from src.presentation.ui.components.toolbar_constants import (
    TOOLBAR_LAYOUT,
    TOOLBAR_SIZE,
    TOOLBAR_TEXT,
)
from src.presentation.ui.design.icons import Icons


class Toolbar(QFrame):

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, TOOLBAR_LAYOUT.RIGHT_MARGIN, 0)
        layout.setSpacing(TOOLBAR_LAYOUT.SPACING)
        self.setObjectName("toolbar")
        self.setFixedHeight(TOOLBAR_SIZE.HEIGHT)

        self.save_workspace_action = QAction(TOOLBAR_TEXT.SAVE_WORKSPACE, self)
        self.load_workspace_action = QAction(TOOLBAR_TEXT.LOAD_WORKSPACE, self)

        self.converter_preferences_action = QAction(TOOLBAR_TEXT.CONVERTER, self)
        self.toggle_key_panel_action = QAction(TOOLBAR_TEXT.SHOW_KEY_PANEL, self)
        self.toggle_key_panel_action.setCheckable(True)
        self.toggle_key_panel_action.setChecked(True)
        self.auto_convert_action = QAction(TOOLBAR_TEXT.AUTO_CONVERT, self)
        self.auto_convert_action.setCheckable(True)
        self.auto_convert_action.setChecked(False)
        self.binary_workbench_action = QAction(TOOLBAR_TEXT.BINARY_WORKBENCH, self)
        self.user_guide_action = QAction(TOOLBAR_TEXT.USER_GUIDE, self)
        self.donor_action = QAction(TOOLBAR_TEXT.DONOR, self)

        file_menu = QMenu(self)
        file_menu.addAction(self.save_workspace_action)
        file_menu.addAction(self.load_workspace_action)

        preferences_menu = QMenu(self)
        preferences_menu.addAction(self.converter_preferences_action)
        preferences_menu.addAction(self.toggle_key_panel_action)
        preferences_menu.addAction(self.auto_convert_action)

        tools_menu = QMenu(self)
        tools_menu.addAction(self.binary_workbench_action)

        help_menu = QMenu(self)
        help_menu.addAction(self.user_guide_action)
        help_menu.addAction(self.donor_action)

        self.file_button = self._build_menu_button(TOOLBAR_TEXT.FILE, "file", Icons.file(), file_menu)
        self.tools_button = self._build_menu_button(
            TOOLBAR_TEXT.TOOLS,
            "tools",
            Icons.tools(),
            tools_menu,
        )
        self.preferences_button = self._build_menu_button(
            TOOLBAR_TEXT.PREFERENCES,
            "preferences",
            Icons.preferences(),
            preferences_menu,
        )
        self.help_button = self._build_menu_button(
            TOOLBAR_TEXT.HELP,
            "help",
            Icons.help(),
            help_menu,
        )

        layout.addWidget(self.file_button)
        layout.addWidget(self.tools_button)
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
        button.setIconSize(QSize(TOOLBAR_SIZE.ICON_SIZE, TOOLBAR_SIZE.ICON_SIZE))
        button.setObjectName(object_name)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setMinimumHeight(TOOLBAR_SIZE.ACTION_MIN_HEIGHT)
        button.setMinimumWidth(TOOLBAR_SIZE.ACTION_MIN_WIDTH)
        button.setAutoRaise(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        return button
