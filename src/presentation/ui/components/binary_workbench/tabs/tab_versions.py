from src.core.binary_workbench.context_overlays import compact_binary_context_overlays
from src.core.binary_workbench.file_ops import (
    apply_version_rows,
    build_version_rows_from_overlay,
    overlay_from_version_rows,
)
from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
    without_blank_instruction_overlays,
)
from src.core.binary_workbench.version_instruction_maps import version_instruction_maps
from src.core.binary_workbench.version_line_comments import apply_line_comments
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchVersionDTO
from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.presentation.repository.binary_workbench_workspace.constants import (
    VERSION_PATH_PREFIX,
    VERSIONS,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    apply_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TAB_KIND


class TabVersionsMixin:
    def create_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return False
        current = compact_binary_context_overlays(current)
        version = self._version_from_current(name, current)
        versions = [item for item in current.versions if item.name != name]
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(**{**current.__dict__, "versions": [*versions, version], "active_version_name": name, "version_dirty": True})
        )
        return True

    def update_current_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY or not current.active_version_name:
            return False
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            page.commit_current_editor_text()
            current = page.current_context()
        current = compact_binary_context_overlays(current)
        version = self._version_from_current(name, current)
        versions = [item for item in current.versions if item.name != current.active_version_name]
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(**{**current.__dict__, "versions": [*versions, version], "active_version_name": name, "version_dirty": True})
        )
        return True

    def load_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return False
        current = compact_binary_context_overlays(current)
        version = next((item for item in current.versions if item.name == name), None)
        if version is None:
            return False
        rows = self._rows_from_version(current, version)
        byte_overlays = overlay_from_version_rows(version.rows)
        instruction_overlays = self._instruction_overlays_from_version(current, version)
        if instruction_overlays:
            byte_overlays.update(
                byte_overlays_from_instruction_overlays(
                    instruction_overlays,
                    current.variables,
                    current.equates,
                )
            )
        byte_overlays, instruction_overlays = without_blank_instruction_overlays(
            byte_overlays,
            instruction_overlays,
        )
        self._set_current_context(
            compact_binary_context_overlays(BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "rows": rows,
                    "read_mode": "assembly" if version.instructions_by_line else current.read_mode,
                    "byte_overlays": byte_overlays,
                    "instruction_overlays": instruction_overlays,
                    "active_version_name": name,
                    "version_dirty": False,
                }
            ))
        )
        return True

    def load_versions_file(self, path) -> str | None:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return None
        loaded = self._workspace_repository.load_versions_file(path)
        if not loaded:
            return None
        active = loaded[0].name
        module_paths = {
            key: value
            for key, value in current.module_paths.items()
            if key != VERSIONS and not key.startswith(VERSION_PATH_PREFIX)
        }
        module_paths[VERSIONS] = str(path)
        module_paths.update({f"{VERSION_PATH_PREFIX}{version.name}": str(path) for version in loaded})
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "versions": loaded,
                    "active_version_name": active,
                    "module_paths": module_paths,
                    "module_directories": {
                        **current.module_directories,
                        "versions": str(path.parent),
                    },
                }
            )
        )
        return active if self.load_version(active) else None

    def _version_from_current(
        self,
        name: str,
        current: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchVersionDTO:
        current = compact_binary_context_overlays(current)
        instruction_overlays, instructions_by_line = version_instruction_maps(
            current.rows,
            current.instruction_overlays,
            binary_workbench_codec_for(current.cpu_arch),
            current.labels,
            current.variables,
            current.equates,
        )
        return BinaryWorkbenchVersionDTO(
            name=name,
            rows=build_version_rows_from_overlay(
                current.byte_overlays,
                list(current.reference_offsets),
                dict(current.reference_offset_bases),
            ),
            instruction_overlays=instruction_overlays,
            instructions_by_line=instructions_by_line,
        )

    def _rows_from_version(
        self,
        current: BinaryWorkbenchTabContextDTO,
        version: BinaryWorkbenchVersionDTO,
    ):
        rows = apply_version_rows(current.original_rows, version.rows) if version.rows else (current.original_rows or current.rows)
        if version.instruction_overlays:
            rows = apply_instruction_overlays(rows, version.instruction_overlays)
        if not version.instructions_by_line:
            return rows
        return apply_line_comments(rows, version.instructions_by_line, list(current.reference_offsets))

    def _instruction_overlays_from_version(
        self,
        current: BinaryWorkbenchTabContextDTO,
        version: BinaryWorkbenchVersionDTO,
    ) -> dict[str, str]:
        if version.instructions_by_line:
            return {
                **version.instruction_overlays,
                **{
                    row.offsets.get("File", "0x00000000"): row.instruction
                    for row in self._rows_from_version(current, version)
                    if row.instruction and row.offsets.get("File") != "-"
                },
            }
        return dict(version.instruction_overlays)
