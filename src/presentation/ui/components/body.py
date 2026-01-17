from PySide6.QtWidgets import QFrame, QHBoxLayout
from src.presentation.ui.components.converter_panel import ConverterPanel
from src.presentation.ui.components.command_panel import CommandPanel


class Body(QFrame):

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        self.setObjectName("body")
        layout.setSpacing(20)  # distância entre ConverterPanel e CommandPanel
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(ConverterPanel(), 1)  # stretch=1
        layout.addWidget(CommandPanel(), 1)    # stretch=1
