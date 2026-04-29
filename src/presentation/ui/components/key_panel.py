from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QPushButton, QSizePolicy

from .flow_layout import FlowLayout
from .key_panel_constants import KEY_PANEL_KEYS, KEY_PANEL_LAYOUT, KEY_PANEL_SIZE


class KeyPanel(QFrame):
    keyPressed = Signal(str)

    def __init__(self):
        super().__init__()

        self.setObjectName("key-panel")
        self.buttons: dict[str, QPushButton] = {}
        layout = FlowLayout(
            self,
            margin=KEY_PANEL_LAYOUT.MARGIN,
            h_spacing=KEY_PANEL_LAYOUT.H_SPACING,
            v_spacing=KEY_PANEL_LAYOUT.V_SPACING,
        )

        for key in KEY_PANEL_KEYS:
            label = "&&" if key == "&" else key
            button = QPushButton(label)
            if key.lower() in ("clear", "enter"):
                button.setObjectName(key.lower())

            button.setMinimumHeight(KEY_PANEL_SIZE.BUTTON_MIN_HEIGHT)
            button.setMinimumWidth(KEY_PANEL_SIZE.BUTTON_MIN_WIDTH)
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _, key=key: self.keyPressed.emit(key))

            self.buttons[key] = button
            layout.addWidget(button)
