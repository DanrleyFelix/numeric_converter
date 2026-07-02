from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.presentation.ui.components import Body, Footer, KeyPanel, Toolbar
from src.presentation.ui.components.command_panel.constants import COMMAND_PANEL_SHORTCUT
from src.presentation.ui.main_window.constants import MAIN_WINDOW_MARGIN, MAIN_WINDOW_SIZE, MAIN_WINDOW_SPACING

if TYPE_CHECKING:
    from src.presentation.ui.main_window.window import MainWindow


class MainWindowLayoutMixin:
    def _build_ui(self: MainWindow) -> None:
        self.toolbar = Toolbar()
        self.body = Body()
        self.key_panel = KeyPanel()
        self.footer = Footer()

        container = QWidget()
        layout_container = QVBoxLayout(container)
        layout_container.setContentsMargins(
            MAIN_WINDOW_MARGIN.CONTAINER_LEFT,
            MAIN_WINDOW_MARGIN.CONTAINER_TOP,
            MAIN_WINDOW_MARGIN.CONTAINER_RIGHT,
            MAIN_WINDOW_MARGIN.CONTAINER_BOTTOM,
        )
        layout_container.setSpacing(MAIN_WINDOW_SPACING.CONTAINER)
        layout_container.addWidget(self.body, 1)
        layout_container.addWidget(self.key_panel)
        layout_container.addWidget(self.footer)
        layout_container.addStretch()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(
            MAIN_WINDOW_MARGIN.CENTRAL_LEFT,
            MAIN_WINDOW_MARGIN.CENTRAL_TOP,
            MAIN_WINDOW_MARGIN.CENTRAL_RIGHT,
            MAIN_WINDOW_MARGIN.CENTRAL_BOTTOM,
        )
        layout.setSpacing(MAIN_WINDOW_SPACING.CENTRAL)
        layout.addWidget(self.toolbar)
        layout.addWidget(container, 1)
        layout.addStretch()
        central.setObjectName("main-window")
        self.setCentralWidget(central)
        self._register_toolbar_actions()

    def _bind_events(self: MainWindow) -> None:
        self.body.converter_panel.inputEdited.connect(self._on_converter_input)
        self.body.command_panel.editor.textChanged.connect(self._on_command_text_changed)
        self.body.command_panel.editor.submitted.connect(self._on_command_submitted)
        self.key_panel.keyPressed.connect(self._on_key_panel_pressed)

        self.toolbar.save_workspace_action.triggered.connect(self._save_workspace)
        self.toolbar.load_workspace_action.triggered.connect(self._load_workspace)
        self.toolbar.binary_workbench_action.triggered.connect(self._open_binary_workbench)
        self.toolbar.converter_preferences_action.triggered.connect(self._open_preferences)
        self.toolbar.log_preferences_action.triggered.connect(self._open_log_preferences)
        self.toolbar.toggle_key_panel_action.toggled.connect(self._on_key_panel_toggled)
        self.toolbar.auto_convert_action.toggled.connect(self._on_auto_convert_toggled)
        self.toolbar.user_guide_action.triggered.connect(self._open_help)
        self.toolbar.donor_action.triggered.connect(self._open_donor)
        self.body.command_panel.show_logs_button.clicked.connect(self._open_logs_window)
        self.body.command_panel.show_variables_button.clicked.connect(self._open_variables_window)
        self._bind_focus_shortcuts()

    def _register_toolbar_actions(self: MainWindow) -> None:
        for action in (
            self.toolbar.save_workspace_action,
            self.toolbar.load_workspace_action,
            self.toolbar.binary_workbench_action,
            self.toolbar.converter_preferences_action,
            self.toolbar.log_preferences_action,
            self.toolbar.toggle_key_panel_action,
            self.toolbar.auto_convert_action,
            self.toolbar.user_guide_action,
            self.toolbar.donor_action,
        ):
            self.addAction(action)

    def _bind_focus_shortcuts(self: MainWindow) -> None:
        self._focus_shortcuts = [
            QShortcut(QKeySequence(key), self, activated=callback)
            for key, callback in (
                ("F1", self.body.focus_decimal),
                ("F2", self.body.focus_binary),
                ("F3", self.body.focus_hex_be),
                ("F4", self.body.focus_hex_le),
                ("F5", self.body.focus_command),
            )
        ]
        self._copy_raw_shortcut = QShortcut(
            QKeySequence("Alt+C"),
            self,
            activated=self._copy_focused_converter_raw,
        )
        self._workspace_window_shortcuts = [
            QShortcut(QKeySequence(key), self, activated=callback)
            for key, callback in (
                (COMMAND_PANEL_SHORTCUT.VARIABLES, self._open_variables_window),
                (COMMAND_PANEL_SHORTCUT.LOGS, self._open_logs_window),
            )
        ]

    def _on_key_panel_toggled(self: MainWindow, visible: bool) -> None:
        if visible and self.key_panel.isHidden():
            self._size_before_key_panel_show = QSize(self.size())
        self.key_panel.setVisible(visible)
        self._update_minimum_height(visible)
        if not visible and self._size_before_key_panel_show is not None:
            self.resize(self._size_before_key_panel_show)
            self._size_before_key_panel_show = None
        self._autosave_state()

    def _on_auto_convert_toggled(self: MainWindow, enabled: bool) -> None:
        self._auto_convert_enabled = enabled
        self._autosave_state()

    def _update_minimum_height(self: MainWindow, key_panel_visible: bool) -> None:
        min_width = MAIN_WINDOW_SIZE.MIN_WIDTH
        min_height = MAIN_WINDOW_SIZE.MIN_HEIGHT + MAIN_WINDOW_SIZE.KEY_PANEL_VISIBLE_EXTRA_HEIGHT
        if not key_panel_visible:
            min_width = MAIN_WINDOW_SIZE.KEY_PANEL_HIDDEN_MIN_WIDTH
            reduction = int(
                self.key_panel.sizeHint().height()
                * MAIN_WINDOW_SIZE.KEY_PANEL_HIDDEN_REDUCTION_RATIO
            )
            min_height = max(400, MAIN_WINDOW_SIZE.MIN_HEIGHT - reduction)
        self.setMinimumSize(min_width, min_height)
