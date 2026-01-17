from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from src.presentation.ui.components import Toolbar, Body, Footer, KeyPanel
from src.presentation.ui.helpers.load_qss import STYLESHEET
from src.presentation.ui.design.icons import Icons


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setMinimumSize(600, 500)
        self.setWindowTitle("Numeric WorkBench")
        self.setWindowIcon(Icons.hexadecimal())

        container = QWidget()
        layout_container = QVBoxLayout(container)
        layout_container.setContentsMargins(16, 16, 16, 16)
        layout_container.setSpacing(16)
        layout_container.addWidget(Body(), 1)
        layout_container.addWidget(KeyPanel())
        layout_container.addWidget(Footer())
        layout_container.addStretch()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(central)

        layout.addWidget(Toolbar())
        layout.addWidget(container, 1)
        layout.addStretch()
        central.setObjectName("main-window")
        self.setStyleSheet(STYLESHEET)
