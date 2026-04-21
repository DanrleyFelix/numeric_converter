from PySide6.QtWidgets import QFrame, QHBoxLayout

from src.presentation.ui.components.command_panel import CommandPanel
from src.presentation.ui.components.converter_panel import ConverterPanel


class Body(QFrame):

    def __init__(self):
        super().__init__()
        self.converter_panel = ConverterPanel()
        self.command_panel = CommandPanel()

        layout = QHBoxLayout(self)
        self.setObjectName("body")
        layout.setSpacing(20)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(self.converter_panel, 1)
        layout.addWidget(self.command_panel, 1)
