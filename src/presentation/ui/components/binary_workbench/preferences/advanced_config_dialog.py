from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QPushButton, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.preferences.constants import (
    BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT,
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
        arch_label = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.CPU_ARCH_LABEL, self)
        arch_label.setObjectName("preferences-section-title")
        self.combo = QComboBox(self)
        self.combo.setObjectName("advanced-config-dropdown")
        self.combo.setCursor(Qt.PointingHandCursor)
        self.combo.addItem(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.OPTION_PSX_MIPS_R3000A)
        self.combo.setCurrentText(
            current_arch or BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.OPTION_PSX_MIPS_R3000A
        )
        read_mode_label = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.READ_MODE_LABEL, self)
        read_mode_label.setObjectName("preferences-section-title")
        self.read_mode_combo = QComboBox(self)
        self.read_mode_combo.setObjectName("advanced-config-dropdown")
        self.read_mode_combo.setCursor(Qt.PointingHandCursor)
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
        self.block_size = QComboBox(self)
        self.block_size.setObjectName("advanced-config-dropdown")
        self.block_size.setCursor(Qt.PointingHandCursor)
        self.block_size.addItems(
            [str(value) for value in BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT.BLOCK_SIZE_OPTIONS]
        )
        self.block_size.setCurrentText(
            str(_nearest_block_size(current_block_size or BINARY_WORKBENCH_LAYOUT.DEFAULT_BLOCK_SIZE))
        )
        cache_label = QLabel(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.CACHE_MAX_BLOCKS_LABEL, self)
        cache_label.setObjectName("preferences-section-title")
        self.cache_max_blocks = QComboBox(self)
        self.cache_max_blocks.setObjectName("advanced-config-dropdown")
        self.cache_max_blocks.setCursor(Qt.PointingHandCursor)
        self.cache_max_blocks.addItems(
            [str(value) for value in BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT.CACHE_MAX_BLOCKS_OPTIONS]
        )
        self.cache_max_blocks.setCurrentText(
            str(
                _nearest_cache_max_blocks(
                    current_cache_max_blocks or BINARY_WORKBENCH_LAYOUT.DEFAULT_CACHE_MAX_BLOCKS
                )
            )
        )
        ok = QPushButton(BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT.CONFIRM, self)
        ok.setObjectName("preferences-confirm")
        ok.setFocusPolicy(Qt.NoFocus)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        for control in (
            self.combo,
            self.read_mode_combo,
            self.block_size,
            self.cache_max_blocks,
            ok,
        ):
            control.setFixedWidth(BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT.CONTROL_WIDTH)
        layout.addWidget(arch_label)
        layout.addWidget(self.combo)
        layout.addWidget(read_mode_label)
        layout.addWidget(self.read_mode_combo)
        layout.addWidget(block_size_label)
        layout.addWidget(self.block_size)
        layout.addWidget(cache_label)
        layout.addWidget(self.cache_max_blocks)
        layout.addSpacing(BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT.CONFIRM_TOP_SPACING)
        layout.addWidget(ok)

    def selected_arch(self) -> str:
        return self.combo.currentText()

    def selected_read_mode(self) -> str:
        return self.read_mode_combo.currentText()

    def selected_block_size(self) -> int:
        return int(self.block_size.currentText())

    def selected_cache_max_blocks(self) -> int:
        return int(self.cache_max_blocks.currentText())


def _nearest_block_size(value: int) -> int:
    options = BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT.BLOCK_SIZE_OPTIONS
    return min(options, key=lambda option: abs(option - value))


def _nearest_cache_max_blocks(value: int) -> int:
    options = BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT.CACHE_MAX_BLOCKS_OPTIONS
    return min(options, key=lambda option: abs(option - value))
