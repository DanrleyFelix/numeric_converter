from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QPushButton, QSpinBox, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.preferences.constants import (
    BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT,
)


class BinaryWorkbenchAdvancedConfigDialog(QDialog):
    def __init__(
        self,
        current_arch: str,
        current_read_mode: str,
        current_block_size: int,
        current_cache_max_blocks: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.TITLE)
        layout = QVBoxLayout(self)
        title = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.TITLE, self)
        title.setObjectName("preferences-title")
        subtitle = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.SUBTITLE, self)
        subtitle.setObjectName("preferences-subtitle")
        subtitle.setWordWrap(True)
        arch_label = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.CPU_ARCH_LABEL, self)
        arch_label.setObjectName("preferences-section-title")
        self.combo = QComboBox(self)
        self.combo.addItem(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.OPTION_PSX_MIPS_R3000A)
        self.combo.setCurrentText(
            current_arch or BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.OPTION_PSX_MIPS_R3000A
        )
        read_mode_label = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.READ_MODE_LABEL, self)
        read_mode_label.setObjectName("preferences-section-title")
        self.read_mode_combo = QComboBox(self)
        self.read_mode_combo.addItems(
            [
                BINARY_WORKBENCH_TEXT.AUTO_READ_MODE,
                BINARY_WORKBENCH_TEXT.BYTES_READ_MODE,
                BINARY_WORKBENCH_TEXT.ASSEMBLY_READ_MODE,
            ]
        )
        self.read_mode_combo.setCurrentText(
            current_read_mode or BINARY_WORKBENCH_TEXT.AUTO_READ_MODE
        )
        block_size_label = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.BLOCK_SIZE_LABEL, self)
        block_size_label.setObjectName("preferences-section-title")
        self.block_size = QSpinBox(self)
        self.block_size.setRange(1, 1024 * 1024)
        self.block_size.setValue(current_block_size or BINARY_WORKBENCH_LAYOUT.DEFAULT_BLOCK_SIZE)
        cache_label = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.CACHE_MAX_BLOCKS_LABEL, self)
        cache_label.setObjectName("preferences-section-title")
        self.cache_max_blocks = QSpinBox(self)
        self.cache_max_blocks.setRange(1, 1_000_000)
        self.cache_max_blocks.setValue(
            current_cache_max_blocks or BINARY_WORKBENCH_LAYOUT.DEFAULT_CACHE_MAX_BLOCKS
        )
        ok = QPushButton("OK", self)
        ok.setObjectName("preferences-ok")
        ok.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(arch_label)
        layout.addWidget(self.combo)
        layout.addWidget(read_mode_label)
        layout.addWidget(self.read_mode_combo)
        layout.addWidget(block_size_label)
        layout.addWidget(self.block_size)
        layout.addWidget(cache_label)
        layout.addWidget(self.cache_max_blocks)
        layout.addWidget(ok, 0, Qt.AlignRight)

    def selected_arch(self) -> str:
        return self.combo.currentText()

    def selected_read_mode(self) -> str:
        return self.read_mode_combo.currentText()

    def selected_block_size(self) -> int:
        return self.block_size.value()

    def selected_cache_max_blocks(self) -> int:
        return self.cache_max_blocks.value()
