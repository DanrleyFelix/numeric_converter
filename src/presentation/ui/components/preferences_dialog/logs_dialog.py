from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.modules.command_window_dtos import CommandLogPreferencesDTO
from src.presentation.ui.components.preferences_dialog.constants import (
    LOG_PREFERENCES_SIZE,
    LOG_PREFERENCES_MARGIN,
    LOG_PREFERENCES_SPACING,
    LOG_PREFERENCES_TEXT,
)


class LogPreferencesDialog(QDialog):

    def __init__(
        self,
        preferences: CommandLogPreferencesDTO,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(LOG_PREFERENCES_TEXT.TITLE)
        self.setModal(True)
        self.setFixedSize(LOG_PREFERENCES_SIZE.WIDTH, LOG_PREFERENCES_SIZE.HEIGHT)
        self._build_ui(preferences)
        self._sync_binary_only_state()

    def selected_preferences(self) -> CommandLogPreferencesDTO:
        return CommandLogPreferencesDTO(
            enabled=self.enabled_box.isChecked(),
            assignment_only=self.assignment_only_box.isChecked(),
            single_unary_only=self.single_unary_only_box.isChecked(),
            no_operator=self.no_operator_box.isChecked(),
            assignment_operator=self.assignment_operator_box.isChecked(),
            binary_operator_only=self.binary_operator_only_box.isChecked(),
        )

    def _build_ui(self, preferences: CommandLogPreferencesDTO) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            LOG_PREFERENCES_MARGIN.ROOT_LEFT,
            LOG_PREFERENCES_MARGIN.ROOT_TOP,
            LOG_PREFERENCES_MARGIN.ROOT_RIGHT,
            LOG_PREFERENCES_MARGIN.ROOT_BOTTOM,
        )
        layout.setSpacing(LOG_PREFERENCES_SPACING.ROOT)

        subtitle = QLabel(LOG_PREFERENCES_TEXT.SUBTITLE)
        subtitle.setObjectName("preferences-subtitle")
        layout.addWidget(subtitle)

        options = QVBoxLayout()
        options.setSpacing(LOG_PREFERENCES_SPACING.OPTIONS)
        self.enabled_box = self._check_box(LOG_PREFERENCES_TEXT.ENABLED, preferences.enabled)
        self.enabled_box.setShortcut(QKeySequence("Alt+L"))
        self.assignment_only_box = self._check_box(
            LOG_PREFERENCES_TEXT.ASSIGNMENT_ONLY,
            preferences.assignment_only,
        )
        self.single_unary_only_box = self._check_box(
            LOG_PREFERENCES_TEXT.SINGLE_UNARY_ONLY,
            preferences.single_unary_only,
        )
        self.no_operator_box = self._check_box(LOG_PREFERENCES_TEXT.NO_OPERATOR, preferences.no_operator)
        self.assignment_operator_box = self._check_box(
            LOG_PREFERENCES_TEXT.ASSIGNMENT_OPERATOR,
            preferences.assignment_operator,
        )
        self.binary_operator_only_box = self._check_box(
            LOG_PREFERENCES_TEXT.BINARY_OPERATOR_ONLY,
            preferences.binary_operator_only,
        )
        for box in (
            self.enabled_box,
            self.assignment_only_box,
            self.single_unary_only_box,
            self.no_operator_box,
            self.assignment_operator_box,
            self.binary_operator_only_box,
        ):
            options.addWidget(box)
        layout.addLayout(options)
        layout.addStretch(1)
        self._add_buttons(layout)
        self.enabled_box.toggled.connect(self._on_enabled_toggled)
        self.binary_operator_only_box.toggled.connect(self._on_binary_only_toggled)

    def _check_box(self, text: str, checked: bool) -> QCheckBox:
        box = QCheckBox(text)
        box.setChecked(checked)
        box.setCursor(Qt.PointingHandCursor)
        return box

    def _add_buttons(self, layout: QVBoxLayout) -> None:
        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(
            LOG_PREFERENCES_MARGIN.BUTTONS_LEFT,
            LOG_PREFERENCES_MARGIN.BUTTONS_TOP,
            LOG_PREFERENCES_MARGIN.BUTTONS_RIGHT,
            LOG_PREFERENCES_MARGIN.BUTTONS_BOTTOM,
        )
        buttons_row.setSpacing(LOG_PREFERENCES_SPACING.BUTTONS)
        cancel_button = QPushButton(LOG_PREFERENCES_TEXT.CANCEL)
        ok_button = QPushButton(LOG_PREFERENCES_TEXT.OK)
        for button in (ok_button, cancel_button):
            button.setMinimumWidth(LOG_PREFERENCES_SIZE.ACTION_BUTTON_WIDTH)
            button.setMinimumHeight(LOG_PREFERENCES_SIZE.ACTION_BUTTON_HEIGHT)
            button.setCursor(Qt.PointingHandCursor)
        ok_button.setObjectName("preferences-ok")
        cancel_button.setObjectName("preferences-cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons_row.addWidget(cancel_button, 0, Qt.AlignLeft)
        buttons_row.addStretch(1)
        buttons_row.addWidget(ok_button, 0, Qt.AlignRight)
        layout.addLayout(buttons_row)

    def _on_enabled_toggled(self, checked: bool) -> None:
        if not checked:
            self.binary_operator_only_box.setChecked(False)
        self._sync_binary_only_state()

    def _on_binary_only_toggled(self, checked: bool) -> None:
        if checked:
            self.enabled_box.setChecked(True)
            for box in self._specific_filter_boxes():
                box.setChecked(False)
        self._sync_binary_only_state()

    def _sync_binary_only_state(self) -> None:
        enabled = self.enabled_box.isChecked()
        binary_only = self.binary_operator_only_box.isChecked()
        for box in self._specific_filter_boxes():
            box.setEnabled(enabled and not binary_only)
        self.binary_operator_only_box.setEnabled(enabled)

    def _specific_filter_boxes(self) -> tuple[QCheckBox, QCheckBox, QCheckBox, QCheckBox]:
        return (
            self.assignment_only_box,
            self.single_unary_only_box,
            self.no_operator_box,
            self.assignment_operator_box,
        )
