from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFrame, QLineEdit, QVBoxLayout, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO, BinaryWorkbenchLbaFilesystemDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.file_dialogs.constants import (
    BINARY_WORKBENCH_FILE_DIALOG_TEXT,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_json import (
    LbaFilesystemJsonMixin,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_layout import (
    LbaFilesystemLayoutMixin,
)
from src.presentation.ui.components.binary_workbench.file_dialogs.lba_filesystem_rows import (
    LbaFilesystemRowsMixin,
)


class BinaryWorkbenchLbaFilesystemDialog(
    LbaFilesystemJsonMixin,
    LbaFilesystemLayoutMixin,
    LbaFilesystemRowsMixin,
    QDialog,
):
    directoryChanged = Signal(str)
    goToRequested = Signal(int)

    def __init__(
        self,
        internal_files: list[BinaryWorkbenchInternalFileDTO],
        lba_sector_size: int = 2352,
        libraries: list[BinaryWorkbenchLbaFilesystemDTO] | None = None,
        default_library_name: str = "",
        default_directory: str = "",
        parent=None,
    ) -> None:
        if parent is None and not isinstance(lba_sector_size, int):
            parent = lba_sector_size
            lba_sector_size = 2352
        if parent is None and default_directory and not isinstance(default_directory, str):
            parent = default_directory
            default_directory = ""
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_FILE_DIALOG_TEXT.LBA_TITLE)
        self.setMinimumSize(BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_MIN_WIDTH, BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_MIN_HEIGHT)
        self.setMaximumSize(
            BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_MAX_WIDTH,
            BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_MAX_HEIGHT,
        )
        self.resize(BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_WIDTH, BINARY_WORKBENCH_LAYOUT.LBA_DIALOG_HEIGHT)
        self._libraries = {item.name: item for item in libraries or []}
        self._library_directory = default_directory
        self._save_requested = False
        self._saved_library_name = ""
        self._saved_library_path = ""
        self._loaded_library_name = ""
        self._loaded_library_path = ""
        self._rows: list[tuple[QLineEdit, QLineEdit, QWidget, QWidget]] = []
        self._build_dialog(internal_files, default_library_name, lba_sector_size)

    def _build_dialog(
        self,
        internal_files: list[BinaryWorkbenchInternalFileDTO],
        default_library_name: str,
        lba_sector_size: int,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        self.shell = QFrame(self)
        self.shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(20, 20, 20, 16)
        shell_layout.setSpacing(12)
        self._build_library_controls(shell_layout, default_library_name, lba_sector_size)
        self._build_entry(shell_layout)
        self._build_rows(shell_layout, internal_files)
        self._build_footer_actions(shell_layout)
        layout.addWidget(self.shell, 1)

    def should_save_library(self) -> bool:
        return self._save_requested

    def library_name(self) -> str:
        return ""

    def loaded_library_name(self) -> str:
        return self._loaded_library_name

    def saved_library_name(self) -> str:
        return self._saved_library_name

    def saved_library_path(self) -> str:
        return self._saved_library_path

    def loaded_library_path(self) -> str:
        return self._loaded_library_path

    def selected_lba_sector_size(self) -> int:
        return int(self.sector_size.currentText().split()[0])
