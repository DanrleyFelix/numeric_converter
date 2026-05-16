from src.core.binary_workbench.file_ops import (
    apply_version_rows,
    build_version_rows_from_overlay,
    overlay_from_version_rows,
)
from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
)
from src.modules.dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchVersionDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TAB_KIND


class TabVersionsMixin:
    def create_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return False
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
        version = next((item for item in current.versions if item.name == name), None)
        if version is None:
            return False
        byte_overlays = overlay_from_version_rows(version.rows)
        instruction_overlays = dict(version.instruction_overlays)
        if instruction_overlays:
            byte_overlays.update(
                byte_overlays_from_instruction_overlays(
                    instruction_overlays,
                    current.variables,
                    current.equates,
                )
            )
        rows = apply_version_rows(current.original_rows, version.rows) if version.rows else current.rows
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "rows": rows,
                    "byte_overlays": byte_overlays,
                    "instruction_overlays": instruction_overlays,
                    "active_version_name": name,
                    "version_dirty": False,
                }
            )
        )
        return True

    def _version_from_current(
        self,
        name: str,
        current: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchVersionDTO:
        return BinaryWorkbenchVersionDTO(
            name=name,
            rows=build_version_rows_from_overlay(
                current.byte_overlays,
                list(current.reference_offsets),
                dict(current.reference_offset_bases),
            ),
            instruction_overlays=dict(current.instruction_overlays),
        )
