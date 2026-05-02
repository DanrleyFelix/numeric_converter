from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QPushButton, QVBoxLayout

from src.presentation.ui.components.binary_workbench.preferences.constants import (
    BINARY_WORKBENCH_CPU_ARCH_TEXT,
)


class BinaryWorkbenchCpuArchDialog(QDialog):
    def __init__(self, current_arch: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_CPU_ARCH_TEXT.TITLE)
        layout = QVBoxLayout(self)
        title = QLabel(BINARY_WORKBENCH_CPU_ARCH_TEXT.TITLE, self)
        title.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_CPU_ARCH_TEXT.SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        self.combo = QComboBox(self)
        self.combo.addItem(BINARY_WORKBENCH_CPU_ARCH_TEXT.OPTION_PSX_MIPS_R3000A)
        self.combo.setCurrentText(current_arch or BINARY_WORKBENCH_CPU_ARCH_TEXT.OPTION_PSX_MIPS_R3000A)
        ok = QPushButton("OK", self)
        ok.setObjectName("preferences-ok")
        ok.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.combo)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def selected_arch(self) -> str:
        return self.combo.currentText()
