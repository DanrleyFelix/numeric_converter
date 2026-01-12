from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget
from PySide6.QtCore import QSize, Qt


class IconLabel(QWidget):

    def __init__(
        self,
        icon,
        text: str,
        icon_size: int = 16,
        spacing: int = 6,
        parent=None):

        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        icon_label = QLabel()
        icon_label.setFixedSize(icon_size, icon_size)
        icon_label.setPixmap(icon.pixmap(QSize(icon_size, icon_size)))
        icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        text_label = QLabel(text)
        text_label.setObjectName("IconLabelText")

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
