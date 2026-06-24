from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu, QToolButton

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.toolbar_constants import TOOLBAR_LAYOUT, TOOLBAR_SIZE
from src.presentation.ui.design.icons import Icons


class BinaryWorkbenchToolbar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("toolbar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, TOOLBAR_LAYOUT.RIGHT_MARGIN, 0)
        layout.setSpacing(TOOLBAR_LAYOUT.SPACING)

        self.open_file_action = QAction(BINARY_WORKBENCH_TEXT.OPEN_FILE, self)
        self.open_binary_action = self.open_file_action
        self.new_scratch_action = QAction(BINARY_WORKBENCH_TEXT.NEW_SCRATCH_CODE, self)
        self.open_internal_action = QAction(BINARY_WORKBENCH_TEXT.OPEN_INTERNAL_FILE, self)
        self.version_action = QAction(BINARY_WORKBENCH_TEXT.VERSION, self)
        self.save_version_action = QAction(BINARY_WORKBENCH_TEXT.ATT_CURRENT_VERSION, self)
        self.save_binary_file_action = QAction(BINARY_WORKBENCH_TEXT.SAVE_BINARY_FILE, self)
        self.symbols_action = QAction(BINARY_WORKBENCH_TEXT.SYMBOLS, self)
        self.labels_action = QAction(BINARY_WORKBENCH_TEXT.LABELS, self)
        self.lba_filesystem_action = QAction(BINARY_WORKBENCH_TEXT.LBA_FILESYSTEM, self)
        self.offset_regions_action = QAction(BINARY_WORKBENCH_TEXT.OFFSET_REGIONS, self)
        self.commands_action = QAction(BINARY_WORKBENCH_TEXT.COMMANDS, self)
        self.encoding_tables_action = QAction(BINARY_WORKBENCH_TEXT.ENCODING_TABLES, self)
        self.view_action = QAction(BINARY_WORKBENCH_TEXT.VIEW, self)
        self.advanced_configuration_action = QAction(
            BINARY_WORKBENCH_TEXT.ADVANCED_CONFIGURATION,
            self,
        )
        self.bytes_formatter_action = QAction(BINARY_WORKBENCH_TEXT.BYTES_FORMATTER, self)
        self.reference_offsets_action = QAction(BINARY_WORKBENCH_TEXT.REFERENCE_OFFSETS, self)
        self.rules_action = QAction(BINARY_WORKBENCH_TEXT.RULES, self)
        self.go_to_action = QAction(BINARY_WORKBENCH_TEXT.GO_TO, self)
        self.find_action = QAction(BINARY_WORKBENCH_TEXT.FIND, self)
        self.select_block_action = QAction(BINARY_WORKBENCH_TEXT.SELECT_BLOCK, self)
        self.select_all_action = QAction(BINARY_WORKBENCH_TEXT.SELECT_ALL, self)
        self.help_action = QAction(BINARY_WORKBENCH_TEXT.HELP, self)
        self.open_file_action.setShortcut(QKeySequence("Ctrl+O"))
        self.new_scratch_action.setShortcut(QKeySequence("Ctrl+N"))
        self.open_internal_action.setShortcut(QKeySequence("Alt+I"))
        self.version_action.setShortcut(QKeySequence("Alt+V"))
        self.save_version_action.setShortcut(QKeySequence("Alt+S"))
        self.save_binary_file_action.setShortcut(QKeySequence("Ctrl+S"))
        self.go_to_action.setShortcut(QKeySequence("Ctrl+G"))
        self.find_action.setShortcut(QKeySequence("Ctrl+F"))
        self.select_block_action.setShortcut(QKeySequence("Ctrl+E"))
        self.select_block_action.setShortcutContext(Qt.ApplicationShortcut)
        self.select_all_action.setShortcut(QKeySequence("Ctrl+A"))

        layout.addWidget(self._build_menu_button(BINARY_WORKBENCH_TEXT.FILE, Icons.file(), [
            self.open_file_action,
            self.new_scratch_action,
            self.open_internal_action,
            self.version_action,
            self.save_binary_file_action,
        ]))
        layout.addWidget(self._build_menu_button(BINARY_WORKBENCH_TEXT.ENVIRONMENT, Icons.environment(), [
            self.symbols_action,
            self.labels_action,
            self.lba_filesystem_action,
            self.offset_regions_action,
            self.commands_action,
            self.encoding_tables_action,
        ]))
        layout.addWidget(self._build_menu_button(BINARY_WORKBENCH_TEXT.PREFERENCES, Icons.preferences(), [
            self.bytes_formatter_action,
            self.reference_offsets_action,
            self.view_action,
            self.rules_action,
            self.advanced_configuration_action,
        ]))
        layout.addWidget(self._build_menu_button(BINARY_WORKBENCH_TEXT.SEARCH, Icons.search(), [
            self.go_to_action,
            self.find_action,
            self.select_block_action,
        ]))
        layout.addWidget(self._build_action_button(BINARY_WORKBENCH_TEXT.HELP, Icons.help(), self.help_action))
        layout.addStretch(1)

    def _build_menu_button(self, text: str, icon, actions: list[QAction]) -> QToolButton:
        menu = QMenu(self)
        for action in actions:
            menu.addAction(action)
        button = self._build_base_button(text, icon)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setMenu(menu)
        return button

    def _build_action_button(self, text: str, icon, action: QAction) -> QToolButton:
        button = self._build_base_button(text, icon)
        button.clicked.connect(action.trigger)
        return button

    def _build_base_button(self, text: str, icon) -> QToolButton:
        button = QToolButton()
        button.setText(f"  {text}")
        button.setIcon(icon)
        button.setIconSize(QSize(TOOLBAR_SIZE.ICON_SIZE, TOOLBAR_SIZE.ICON_SIZE))
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setMinimumHeight(TOOLBAR_SIZE.ACTION_MIN_HEIGHT)
        button.setMinimumWidth(TOOLBAR_SIZE.ACTION_MIN_WIDTH)
        button.setAutoRaise(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        return button
