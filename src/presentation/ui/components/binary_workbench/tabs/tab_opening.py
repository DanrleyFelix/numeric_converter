from pathlib import Path

from src.core.binary_workbench.internal_file_region import define_internal_file_region
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_STATE,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.utils import read_json
from src.presentation.repository.binary_workbench_workspace.constants import (
    SCHEMA_VERSION,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.tabs.factory import (
    create_assembly_tab,
    create_binary_tab,
    create_file_tab,
    create_internal_tab,
    create_label_tab,
    create_scratch_tab,
)


class TabOpeningMixin:
    def open_binary_path(self, path: Path) -> None:
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_BINARY_DIRECTORY, path)
        self._append_tab(self._apply_matching_workspace(create_binary_tab(self._state, path, self._preferences), path))

    def open_file_path(self, path: Path) -> None:
        if self._activate_open_file_tab(path):
            self.statusWarningChanged.emit(
                BINARY_WORKBENCH_TEXT.STATUS_ALREADY_OPEN_TEMPLATE.format(name=path.name)
            )
            return
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_FILE_DIRECTORY, path)
        self._append_tab(self._apply_matching_workspace(create_file_tab(self._state, path, self._preferences), path))

    def open_assembly_path(self, path: Path) -> None:
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_ASSEMBLY_DIRECTORY, path)
        self._append_tab(self._apply_matching_workspace(create_assembly_tab(self._state, path, self._preferences), path))

    def open_workspace_path(self, path: Path) -> bool:
        payload = read_json(path)
        if not payload or payload.get("schema_version") != SCHEMA_VERSION:
            return False
        source = payload.get("source")
        if not isinstance(source, dict):
            return False
        filename = source.get("filename")
        directory = source.get("directory")
        if not isinstance(filename, str) or not isinstance(directory, str):
            return False
        source_path = Path(directory) / filename
        if not source_path.exists():
            return False
        self._remember_file_path(BINARY_WORKBENCH_STATE.OPEN_FILE_DIRECTORY, source_path)
        context = create_file_tab(self._state, source_path, self._preferences)
        loaded = self._with_symbol_offsets(
            self._workspace_repository.load_tab_workspace(context, path)
        )
        self._remember_workspace_for_source(loaded)
        self._append_tab(loaded)
        return True

    def new_scratch_tab(self) -> None:
        self._append_tab(create_scratch_tab(self._state))

    def open_internal_tab(self, internal_name: str) -> None:
        current = self.current_context()
        if (
            current is None
            or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY
            or not current.source_path
            or not current.internal_files
        ):
            self.statusWarningChanged.emit(
                BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_REQUIREMENTS
            )
            return
        source = Path(current.source_path)
        target = next((item for item in current.internal_files if item.name == internal_name), None)
        if target is None:
            return
        if self._activate_internal_tab(current, target.start_lba, target.name):
            self.statusWarningChanged.emit(
                BINARY_WORKBENCH_TEXT.STATUS_INTERNAL_ALREADY_OPEN_TEMPLATE.format(name=target.name)
            )
            return
        region = define_internal_file_region(
            source,
            target,
            current.internal_files,
            current.lba_sector_size,
        )
        context = create_internal_tab(self._state, current, target, region)
        self._append_tab(self._apply_matching_internal_workspace(context, source, target.start_lba))

    def open_label_tab(self, label: str, offset: int) -> None:
        self.commit_current_editor_text()
        current = self.current_context()
        if current is None:
            return
        self._append_tab(create_label_tab(current, label))
        self.go_to_instruction_offset(offset)

    def _activate_internal_tab(
        self,
        parent: object,
        start_lba: int,
        name: str,
    ) -> bool:
        parent_source = getattr(parent, "source_path", None)
        for index, tab in enumerate(self._state.tabs):
            if tab.kind != BINARY_WORKBENCH_TAB_KIND.INTERNAL:
                continue
            if tab.display_name != name:
                continue
            if tab.source_path != parent_source:
                continue
            if tab.internal_file_start_lba != start_lba:
                continue
            self.setCurrentIndex(index)
            return True
        return False

    def _activate_open_file_tab(self, path: Path) -> bool:
        target = _resolved_path(path)
        for index, tab in enumerate(self._state.tabs):
            if tab.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL:
                continue
            if tab.display_name != path.name:
                continue
            if _resolved_path(Path(tab.source_path or "")) != target:
                continue
            self.setCurrentIndex(index)
            return True
        return False


def _resolved_path(path: Path) -> str:
    try:
        return str(path.resolve()).casefold()
    except OSError:
        return str(path).casefold()
