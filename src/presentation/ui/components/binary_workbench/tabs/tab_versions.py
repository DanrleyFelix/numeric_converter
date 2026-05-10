from src.core.binary_workbench.file_ops import (
    apply_version_rows,
    build_version_rows_from_overlay,
    overlay_from_version_rows,
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
            BinaryWorkbenchTabContextDTO(**{**current.__dict__, "versions": [*versions, version], "active_version_name": name})
        )
        return True

    def update_current_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY or not current.active_version_name:
            return False
        version = self._version_from_current(name, current)
        versions = [item for item in current.versions if item.name != current.active_version_name]
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(**{**current.__dict__, "versions": [*versions, version], "active_version_name": name})
        )
        return True

    def load_version(self, name: str) -> bool:
        current = self.current_context()
        if current is None or current.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return False
        version = next((item for item in current.versions if item.name == name), None)
        if version is None:
            return False
        rows = apply_version_rows(current.original_rows, version.rows)
        self._set_current_context(
            BinaryWorkbenchTabContextDTO(
                **{**current.__dict__, "rows": rows, "byte_overlays": overlay_from_version_rows(version.rows), "active_version_name": name}
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
        )
