from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from src.presentation.ui.components.footer_constants import FOOTER_LAYOUT, FOOTER_TEXT


class Footer(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("footer")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(FOOTER_LAYOUT.SIDE_MARGIN, 0, FOOTER_LAYOUT.SIDE_MARGIN, 0)
        layout.setSpacing(FOOTER_LAYOUT.SPACING)

        self.footer = QLabel(FOOTER_TEXT.COPYRIGHT)
        self.footer.setObjectName("footer-text")
        self.footer.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.status = QLabel(FOOTER_TEXT.READY)
        self.status.setObjectName("footer-status")
        self.status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self.footer, 1)
        layout.addWidget(self.status, 2)

    def set_status(self, message: str, color: str | None = None) -> None:
        self.status.setText(message)
        self.status.setStyleSheet("" if color is None else f"color: {color};")
