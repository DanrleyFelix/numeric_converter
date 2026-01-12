from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from src.presentation.ui.components.widgets import (
    BaseConverterWidget,
    LogPanelWidget,
    VirtualKeyboardWidget,
    ExpressionWidget)
from PySide6.QtCore import Qt
from src.presentation.ui.design.metrics import Metrics


class NumericWorkbench(QWidget):

    def __init__(self):
        super().__init__()
        self.setObjectName("NumericWorkbench")
        self.setAttribute(Qt.WA_StyledBackground, True)
        root = QVBoxLayout(self)

        top = QHBoxLayout()

        self.converter = BaseConverterWidget()
        self.converter.setObjectName("BaseConverter")
        self.converter.setMinimumWidth(Metrics.CONVERTER_MIN_W)
        self.converter.setMaximumWidth(Metrics.CONVERTER_MAX_W)
        self.converter.setMinimumHeight(Metrics.CONVERTER_MIN_H)
        self.converter.setMaximumHeight(Metrics.CONVERTER_MAX_H)

        self.expression = ExpressionWidget()
        self.expression.setObjectName("Expression")
        self.expression.setMinimumWidth(Metrics.COMMAND_MIN_W)
        self.expression.setMinimumHeight(Metrics.COMMAND_MIN_H)
        self.expression.setMaximumHeight(Metrics.COMMAND_MAX_H)

        self.log_panel = LogPanelWidget()
        self.log_panel.setObjectName("LogPanel")
        self.log_panel.setMinimumWidth(Metrics.LOG_MIN_W)
        self.log_panel.setMaximumWidth(Metrics.LOG_MAX_W)
        self.log_panel.setVisible(False)

        top.addWidget(self.converter, 1)
        top.addWidget(self.expression, 1)
        top.addWidget(self.log_panel, 0)

        self.keyboard = VirtualKeyboardWidget()
        self.keyboard.setObjectName("VirtualKeyboard")
        self.keyboard.setMinimumHeight(Metrics.KEYBOARD_MIN_H)
        self.keyboard.setMaximumHeight(Metrics.KEYBOARD_MAX_H)

        root.addLayout(top, 1)
        root.addWidget(self.keyboard, 0)
        self.setObjectName("NumericWorkbench")

    def render(self, vm):
        self.expression.input.setPlainText(vm.input_text)
        self.expression.input.setEnabled(vm.input_enabled)
        self.log_panel.setVisible(vm.log_visible)
