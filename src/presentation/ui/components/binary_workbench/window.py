from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QVBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchStateDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.preferences import (
    BinaryWorkbenchCpuArchDialog,
)
from src.presentation.ui.components.binary_workbench.tabs import BinaryWorkbenchTabs
from src.presentation.ui.components.binary_workbench.toolbar import BinaryWorkbenchToolbar


class BinaryWorkbenchWindow(QMainWindow):
    sizePersistRequested = Signal(int, int)
    stateChanged = Signal(object)

    def __init__(self, state: BinaryWorkbenchStateDTO):
        super().__init__()
        self.setObjectName("binary-workbench-window")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.TITLE)
        self.setMinimumSize(BINARY_WORKBENCH_LAYOUT.MIN_WIDTH, BINARY_WORKBENCH_LAYOUT.MIN_HEIGHT)
        self.resize(BINARY_WORKBENCH_LAYOUT.WINDOW_WIDTH, BINARY_WORKBENCH_LAYOUT.WINDOW_HEIGHT)
        self.toolbar = BinaryWorkbenchToolbar()
        self.tabs = BinaryWorkbenchTabs(state)
        self.tabs.statusChanged.connect(self.statusBar().showMessage)
        self.tabs.stateChanged.connect(self.stateChanged.emit)
        self._connect_actions()
        self._build_ui()
        self.statusBar().showMessage(BINARY_WORKBENCH_TEXT.STATUS_IDLE)

    def export_state(self) -> BinaryWorkbenchStateDTO:
        return self.tabs.export_state()

    def load_state(self, state: BinaryWorkbenchStateDTO) -> None:
        self.tabs.load_state(state)

    def open_binary_path(self, path: Path) -> None:
        self.tabs.open_binary_path(path)

    def open_assembly_path(self, path: Path) -> None:
        self.tabs.open_assembly_path(path)

    def new_scratch_tab(self) -> None:
        self.tabs.new_scratch_tab()

    def open_internal_tab(self) -> None:
        self.tabs.open_internal_tab()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.sizePersistRequested.emit(self.width(), self.height())
        super().closeEvent(event)

    def _connect_actions(self) -> None:
        self.toolbar.open_binary_action.triggered.connect(lambda: self._open_file(BINARY_WORKBENCH_TEXT.FILE_FILTER_BINARY, self.tabs.open_binary_path))
        self.toolbar.open_assembly_action.triggered.connect(lambda: self._open_file(BINARY_WORKBENCH_TEXT.FILE_FILTER_ASSEMBLY, self.tabs.open_assembly_path))
        self.toolbar.new_scratch_action.triggered.connect(self.tabs.new_scratch_tab)
        self.toolbar.open_internal_action.triggered.connect(self.tabs.open_internal_tab)
        self.toolbar.cpu_arch_action.triggered.connect(self._open_cpu_arch_preferences)
        for action in self._placeholder_actions():
            action.triggered.connect(lambda _, name=action.text(): self.statusBar().showMessage(BINARY_WORKBENCH_TEXT.STATUS_PLACEHOLDER_TEMPLATE.format(name=name), 3000))

    def _build_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("binary-workbench-shell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(BINARY_WORKBENCH_LAYOUT.BODY_LEFT, BINARY_WORKBENCH_LAYOUT.BODY_TOP, BINARY_WORKBENCH_LAYOUT.BODY_RIGHT, BINARY_WORKBENCH_LAYOUT.BODY_BOTTOM)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.BODY_SPACING)
        layout.addWidget(self.tabs, 1)
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.toolbar)
        root.addWidget(shell, 1)
        self.setCentralWidget(central)

    def _open_file(self, file_filter: str, callback) -> None:
        path, _ = QFileDialog.getOpenFileName(self, BINARY_WORKBENCH_TEXT.TITLE, "", file_filter)
        if path:
            callback(Path(path))

    def _open_cpu_arch_preferences(self) -> None:
        current = self.tabs.current_context()
        dialog = BinaryWorkbenchCpuArchDialog(current.cpu_arch if current else "", self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.tabs.set_current_cpu_arch(dialog.selected_arch())

    def _placeholder_actions(self):
        return (
            self.toolbar.create_version_action,
            self.toolbar.att_current_version_action,
            self.toolbar.load_version_action,
            self.toolbar.save_binary_file_action,
            self.toolbar.symbols_action,
            self.toolbar.regions_action,
            self.toolbar.lba_filesystem_action,
            self.toolbar.labels_action,
            self.toolbar.encoding_tables_action,
            self.toolbar.bytes_formatter_action,
            self.toolbar.reference_offsets_action,
            self.toolbar.visible_columns_action,
            self.toolbar.hex_view_action,
            self.toolbar.navigation_mode_action,
            self.toolbar.view_action,
            self.toolbar.advanced_configuration_action,
            self.toolbar.go_to_action,
            self.toolbar.find_action,
            self.toolbar.replace_action,
            self.toolbar.select_block_action,
            self.toolbar.select_all_action,
            self.toolbar.help_action,
        )
