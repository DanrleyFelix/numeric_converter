from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from src.modules.dtos import BinaryWorkbenchStateDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment import (
    BinaryWorkbenchSymbolsDialog,
)
from src.presentation.ui.components.binary_workbench.file_dialogs import (
    BinaryWorkbenchInternalFileDialog,
    BinaryWorkbenchLbaFilesystemDialog,
    BinaryWorkbenchVersionNameDialog,
    BinaryWorkbenchVersionPickerDialog,
)
from src.presentation.ui.components.binary_workbench.preferences import (
    BinaryWorkbenchAdvancedConfigDialog,
    BinaryWorkbenchBytesFormatterDialog,
    BinaryWorkbenchReferenceOffsetsDialog,
)
from src.presentation.ui.components.binary_workbench.search import (
    BinaryWorkbenchFindDialog,
    BinaryWorkbenchGoToDialog,
    BinaryWorkbenchSelectBlockDialog,
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
        self.footer_status = QLabel(BINARY_WORKBENCH_TEXT.STATUS_IDLE, self)
        self.footer_status.setObjectName("binary-workbench-footer-status")
        self.statusBar().hide()
        self.tabs.statusChanged.connect(self._show_status)
        self.tabs.stateChanged.connect(self.stateChanged.emit)
        self.tabs.closeRequested.connect(self._request_tab_close)
        self._connect_actions()
        self._build_ui()
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_IDLE)

    def export_state(self) -> BinaryWorkbenchStateDTO:
        return self.tabs.export_state()

    def load_state(self, state: BinaryWorkbenchStateDTO) -> None:
        self.tabs.load_state(state)

    def open_binary_path(self, path: Path) -> None:
        self.tabs.open_binary_path(path)

    def open_file_path(self, path: Path) -> None:
        self.tabs.open_file_path(path)

    def open_assembly_path(self, path: Path) -> None:
        self.tabs.open_assembly_path(path)

    def new_scratch_tab(self) -> None:
        self.tabs.new_scratch_tab()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.sizePersistRequested.emit(self.width(), self.height())
        super().closeEvent(event)

    def _connect_actions(self) -> None:
        self.toolbar.open_file_action.triggered.connect(self._open_any_file)
        self.toolbar.new_scratch_action.triggered.connect(self.tabs.new_scratch_tab)
        self.toolbar.open_internal_action.triggered.connect(self._open_internal_file)
        self.toolbar.create_version_action.triggered.connect(self._create_version)
        self.toolbar.att_current_version_action.triggered.connect(self._update_version)
        self.toolbar.load_version_action.triggered.connect(self._load_version)
        self.toolbar.save_binary_file_action.triggered.connect(self._save_current_tab)
        self.toolbar.lba_filesystem_action.triggered.connect(self._open_lba_filesystem)
        self.toolbar.symbols_action.triggered.connect(self._open_symbols)
        self.toolbar.bytes_formatter_action.triggered.connect(self._open_bytes_formatter)
        self.toolbar.reference_offsets_action.triggered.connect(self._open_reference_offsets)
        self.toolbar.go_to_action.triggered.connect(self._open_go_to)
        self.toolbar.find_action.triggered.connect(self._open_find)
        self.toolbar.select_block_action.triggered.connect(self._open_select_block)
        self.addActions([
            self.toolbar.go_to_action,
            self.toolbar.find_action,
            self.toolbar.select_block_action,
            self.toolbar.open_file_action,
            self.toolbar.new_scratch_action,
            self.toolbar.save_binary_file_action,
        ])
        self.toolbar.advanced_configuration_action.triggered.connect(
            self._open_advanced_configuration
        )
        for action in self._placeholder_actions():
            action.triggered.connect(lambda _, name=action.text(): self._show_status(BINARY_WORKBENCH_TEXT.STATUS_PLACEHOLDER_TEMPLATE.format(name=name), 3000))

    def _build_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("binary-workbench-shell")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(BINARY_WORKBENCH_LAYOUT.BODY_LEFT, BINARY_WORKBENCH_LAYOUT.BODY_TOP, BINARY_WORKBENCH_LAYOUT.BODY_RIGHT, BINARY_WORKBENCH_LAYOUT.BODY_BOTTOM)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.STATUS_TOP_MARGIN)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.footer_status, 0, Qt.AlignLeft)
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.toolbar)
        root.addWidget(shell, 1)
        self.setCentralWidget(central)

    def _open_file(self, action_key: str, file_filter: str, callback) -> None:
        default_directory = self.tabs.directory_for(action_key)
        path, _ = QFileDialog.getOpenFileName(
            self,
            BINARY_WORKBENCH_TEXT.TITLE,
            default_directory,
            file_filter,
        )
        if path:
            callback(Path(path))

    def _open_any_file(self) -> None:
        self._open_file(
            BINARY_WORKBENCH_STATE.OPEN_FILE_DIRECTORY,
            BINARY_WORKBENCH_TEXT.FILE_FILTER_ANY,
            self.tabs.open_file_path,
        )

    def _open_advanced_configuration(self) -> None:
        current = self.tabs.current_context()
        dialog = BinaryWorkbenchAdvancedConfigDialog(
            current.cpu_arch if current else "",
            current.read_mode if current else BINARY_WORKBENCH_TEXT.AUTO_READ_MODE,
            current.block_size if current else BINARY_WORKBENCH_LAYOUT.DEFAULT_BLOCK_SIZE,
            current.cache_max_blocks if current else BINARY_WORKBENCH_LAYOUT.DEFAULT_CACHE_MAX_BLOCKS,
            self,
        )
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.tabs.set_current_advanced_config(
                dialog.selected_arch(),
                dialog.selected_read_mode(),
                dialog.selected_block_size(),
                dialog.selected_cache_max_blocks(),
            )

    def _open_lba_filesystem(self) -> None:
        current = self.tabs.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_BINARY_REQUIRED, 3000)
            return
        dialog = BinaryWorkbenchLbaFilesystemDialog(current.internal_files, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.tabs.set_current_internal_files(dialog.mappings())

    def _open_symbols(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchSymbolsDialog(current.variables, current.equates, current.labels, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        variables, equates, labels = dialog.values()
        self.tabs.set_current_symbols(variables, equates, labels)

    def _open_bytes_formatter(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchBytesFormatterDialog(current.view_preferences.group_bytes, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.tabs.set_current_group_bytes(dialog.selected_group_bytes())

    def _open_reference_offsets(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchReferenceOffsetsDialog(
            current.reference_offsets,
            current.reference_offset_bases,
            current.view_preferences.visible_columns,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        offsets, bases, visible = dialog.values()
        self.tabs.set_current_reference_offsets(offsets, bases, visible)

    def _open_go_to(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        dialog = BinaryWorkbenchGoToDialog(current, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        offsets = dialog.selected_offsets()
        if not offsets:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_TARGET_PENDING, 3000)
            return
        self.tabs.go_to_offset(offsets[0])
        if len(offsets) > 1:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_MULTIPLE_TARGETS, 3000)

    def _open_find(self) -> None:
        dialog = BinaryWorkbenchFindDialog(self.tabs.find_offsets, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        offset = dialog.selected_offset()
        if offset is None:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NOT_FOUND, 3000)
            return
        self.tabs.go_to_offset(offset)

    def _open_select_block(self) -> None:
        dialog = BinaryWorkbenchSelectBlockDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        selected = dialog.selected_range()
        if selected is not None:
            self.tabs.select_block(*selected)

    def _open_internal_file(self) -> None:
        current = self.tabs.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_BINARY_REQUIRED, 3000)
            return
        if not current.internal_files:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_FILES_REQUIRED, 3000)
            return
        dialog = BinaryWorkbenchInternalFileDialog(current.internal_files, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        name = dialog.selected_name()
        if name is not None:
            self.tabs.open_internal_tab(name)

    def _create_version(self) -> None:
        dialog = BinaryWorkbenchVersionNameDialog(BINARY_WORKBENCH_TEXT.CREATE_VERSION, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.version_name():
            return
        if self.tabs.create_version(dialog.version_name()):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_CREATED_TEMPLATE.format(name=dialog.version_name()), 3000)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_BINARY_REQUIRED, 3000)

    def _update_version(self) -> None:
        current = self.tabs.current_context()
        initial_name = current.active_version_name if current is not None else ""
        dialog = BinaryWorkbenchVersionNameDialog(BINARY_WORKBENCH_TEXT.ATT_CURRENT_VERSION, initial_name, self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.version_name():
            return
        if self.tabs.update_current_version(dialog.version_name()):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_UPDATED_TEMPLATE.format(name=dialog.version_name()), 3000)
            return
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, 3000)

    def _load_version(self) -> None:
        current = self.tabs.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY or not current.versions:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_VERSIONS, 3000)
            return
        dialog = BinaryWorkbenchVersionPickerDialog(current.versions, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        name = dialog.selected_name()
        if name is not None and self.tabs.load_version(name):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_LOADED_TEMPLATE.format(name=name), 3000)

    def _save_file(self) -> bool:
        default_directory = self.tabs.directory_for(BINARY_WORKBENCH_STATE.SAVE_FILE_DIRECTORY)
        current = self.tabs.current_context()
        if not default_directory and current is not None and current.source_path:
            default_directory = str(Path(current.source_path).parent)
        path, _ = QFileDialog.getSaveFileName(
            self,
            BINARY_WORKBENCH_TEXT.SAVE_BINARY_FILE,
            default_directory,
            BINARY_WORKBENCH_TEXT.FILE_FILTER_OUTPUT,
        )
        if not path:
            return False
        if self.tabs.save_current_binary_copy(Path(path)):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_FILE_SAVED_TEMPLATE.format(name=Path(path).name), 3000)
            return True
        self._show_status(BINARY_WORKBENCH_TEXT.STATUS_VERSION_REQUIRED, 3000)
        return False

    def _save_assembly_code(self) -> bool:
        default_directory = self.tabs.directory_for(BINARY_WORKBENCH_STATE.SAVE_ASSEMBLY_DIRECTORY)
        current = self.tabs.current_context()
        if not default_directory and current is not None and current.source_path:
            default_directory = str(Path(current.source_path).parent)
        path, _ = QFileDialog.getSaveFileName(
            self,
            BINARY_WORKBENCH_TEXT.SAVE_ASSEMBLY_CODE,
            default_directory,
            BINARY_WORKBENCH_TEXT.FILE_FILTER_ASSEMBLY,
        )
        if not path:
            return False
        if self.tabs.save_current_assembly_copy(Path(path)):
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_FILE_SAVED_TEMPLATE.format(name=Path(path).name), 3000)
            return True
        return False

    def _save_current_tab(self) -> None:
        current = self.tabs.current_context()
        if current is None:
            return
        focused = self.tabs.focused_editor_kind()
        if focused == BINARY_WORKBENCH_TEXT.BYTES:
            self._save_file()
            return
        if focused != BINARY_WORKBENCH_TEXT.INSTRUCTION:
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_NO_FOCUSED_EDITOR, 3000)
            return
        if current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY and current.source_path and self.tabs.save_current_source_file():
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_FILE_SAVED_TEMPLATE.format(name=Path(current.source_path).name), 3000)
            return
        self._save_assembly_code()

    def _request_tab_close(self, index: int) -> None:
        if not self.tabs.has_unsaved_changes(index):
            self.tabs.close_tab(index)
            return
        self.tabs.setCurrentIndex(index)
        response = self._native_close_question()
        if response == QMessageBox.StandardButton.Cancel:
            return
        if response == QMessageBox.StandardButton.Save and not self._save_current_tab_for_close():
            return
        self.tabs.close_tab(index)

    def _native_close_question(self) -> QMessageBox.StandardButton:
        app = QApplication.instance()
        previous_style = app.styleSheet() if app is not None else ""
        if app is not None:
            app.setStyleSheet("")
        try:
            return QMessageBox.question(
                self,
                BINARY_WORKBENCH_TEXT.TITLE,
                BINARY_WORKBENCH_TEXT.SAVE_BEFORE_CLOSE,
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
        finally:
            if app is not None:
                app.setStyleSheet(previous_style)

    def _save_current_tab_for_close(self) -> bool:
        current = self.tabs.current_context()
        if current is None:
            return False
        if current.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            return self._save_file()
        if current.source_path and self.tabs.save_current_source_file():
            self._show_status(BINARY_WORKBENCH_TEXT.STATUS_FILE_SAVED_TEMPLATE.format(name=Path(current.source_path).name), 3000)
            return True
        return self._save_assembly_code()

    def _show_status(self, message: str, timeout: int = 0) -> None:
        self.footer_status.setText(message)
        self.statusBar().showMessage(message, timeout)

    def _placeholder_actions(self):
        return (
            self.toolbar.regions_action,
            self.toolbar.encoding_tables_action,
            self.toolbar.view_action,
            self.toolbar.select_all_action,
            self.toolbar.help_action,
        )
