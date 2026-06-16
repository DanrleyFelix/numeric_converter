from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QMainWindow, QVBoxLayout, QWidget

from src.presentation.ui.components.donor.constants import DONOR_LAYOUT, DONOR_TEXT


class DonorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("donor-window")
        self.setWindowTitle(DONOR_TEXT.TITLE)
        self.resize(DONOR_LAYOUT.WINDOW_WIDTH, DONOR_LAYOUT.WINDOW_HEIGHT)

        shell = QFrame()
        shell.setObjectName("workspace-table-shell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(
            DONOR_LAYOUT.ROOT_LEFT,
            DONOR_LAYOUT.ROOT_TOP,
            DONOR_LAYOUT.ROOT_RIGHT,
            DONOR_LAYOUT.ROOT_BOTTOM,
        )
        layout.setSpacing(DONOR_LAYOUT.ROOT_SPACING)

        layout.addWidget(self._label("donor-subtitle", DONOR_TEXT.SUBTITLE))
        layout.addWidget(self._card(DONOR_TEXT.PIX_LABEL, DONOR_TEXT.PIX_KEY))
        layout.addWidget(self._card(DONOR_TEXT.BANK_LABEL, DONOR_TEXT.BANK_ACCOUNT))
        layout.addWidget(self._link_card(DONOR_TEXT.PATREON_LABEL, (DONOR_TEXT.PATREON_URL,)))
        layout.addWidget(self._link_card(DONOR_TEXT.LINKS_LABEL, DONOR_TEXT.SUPPORT_LINKS))
        layout.addWidget(
            self._card(
                DONOR_TEXT.OTHER_LABEL,
                "\n".join(DONOR_TEXT.OTHER_SUPPORT_OPTIONS),
            )
        )
        layout.addStretch(1)
        self.setCentralWidget(shell)

    def _card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("workspace-row-card")
        column = QVBoxLayout(card)
        column.setContentsMargins(18, 14, 18, 14)
        column.setSpacing(DONOR_LAYOUT.CARD_SPACING)
        column.addWidget(self._label("donor-section-title", title))
        value_label = self._label("donor-value", value)
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        column.addWidget(value_label)
        return card

    def _label(self, object_name: str, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        return label

    def _link_card(self, title: str, links: tuple[str, ...]) -> QFrame:
        card = self._card(title, "")
        value_label = card.findChild(QLabel, "donor-value")
        if value_label is not None:
            value_label.setText("<br>".join(f'<a href="{link}">{link}</a>' for link in links))
            value_label.setOpenExternalLinks(True)
            value_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        return card
