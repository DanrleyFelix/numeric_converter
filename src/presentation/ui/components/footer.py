from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class Footer(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("footer")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(4)

        self.footer = QLabel("Copyright. Created by Danrley Felix.")
        self.footer.setObjectName("footer-text")
        self.footer.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.status = QLabel("Ready.")
        self.status.setObjectName("footer-status")
        self.status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self.footer, 1)
        layout.addWidget(self.status, 2)

    def set_status(self, message: str, color: str | None = None) -> None:
        self.status.setText(message)
        self.status.setStyleSheet("" if color is None else f"color: {color};")
