from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.presentation.ui.components import Body, Footer, KeyPanel, Toolbar
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

    def _bind_events(self: MainWindow) -> None:
        self.body.converter_panel.inputEdited.connect(self._on_converter_input)
        self.body.command_panel.editor.textChanged.connect(self._on_command_text_changed)
        self.body.command_panel.editor.submitted.connect(self._on_command_submitted)
        self.key_panel.keyPressed.connect(self._on_key_panel_pressed)

        self.toolbar.save_workspace_action.triggered.connect(self._save_workspace)
        self.toolbar.load_workspace_action.triggered.connect(self._load_workspace)
        self.toolbar.converter_preferences_action.triggered.connect(self._open_preferences)
        self.toolbar.toggle_key_panel_action.toggled.connect(self._on_key_panel_toggled)
        self.toolbar.help_button.clicked.connect(self._open_help)
        self.body.command_panel.show_logs_button.clicked.connect(self._open_logs_window)
        self.body.command_panel.show_variables_button.clicked.connect(self._open_variables_window)

    def _on_key_panel_toggled(self: MainWindow, visible: bool) -> None:
        self.key_panel.setVisible(visible)
        self._update_minimum_height(visible)
        self._autosave_state()

    def _update_minimum_height(self: MainWindow, key_panel_visible: bool) -> None:
        min_height = MAIN_WINDOW_SIZE.MIN_HEIGHT
        if not key_panel_visible:
            reduction = int(
                self.key_panel.sizeHint().height()
                * MAIN_WINDOW_SIZE.KEY_PANEL_HIDDEN_REDUCTION_RATIO
            )
            min_height = max(360, MAIN_WINDOW_SIZE.MIN_HEIGHT - reduction)
        self.setMinimumSize(MAIN_WINDOW_SIZE.MIN_WIDTH, min_height)
