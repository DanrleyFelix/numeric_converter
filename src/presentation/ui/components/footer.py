from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PySide6.QtCore import Qt


class Footer(QFrame):
    def __init__(self):
        super().__init__()

        self.setObjectName("footer")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(4)

        footer = QLabel("© All rights reserved. Created by Danrley Felix.")
        footer.setObjectName("footer-text")
        footer.setAlignment(Qt.AlignCenter)

        layout.addWidget(footer)
