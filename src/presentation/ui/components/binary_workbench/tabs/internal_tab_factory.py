from __future__ import annotations

from uuid import uuid4

from src.core.binary_workbench.internal_file_patch import (
    binary_overlays_from_internal_overlays,
    internal_overlays_from_binary_overlays,
)
from src.core.binary_workbench.internal_file_region import InternalFileRegion
from src.core.binary_workbench.internal_offset_mapper import InternalOffsetMapper
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_DEFAULT_VERSION_NAME,
    BINARY_WORKBENCH_TAB_KIND,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
    BinaryWorkbenchVersionDTO,
    BinaryWorkbenchViewPreferencesDTO,
)

from src.presentation.ui.components.binary_workbench.tabs.view_preferences import (
    seed_view_preferences,
)


def create_internal_tab(
    state: BinaryWorkbenchStateDTO,
    parent: BinaryWorkbenchTabContextDTO,
    internal_file: BinaryWorkbenchInternalFileDTO,
    region: InternalFileRegion,
) -> BinaryWorkbenchTabContextDTO:
    version = BinaryWorkbenchVersionDTO(name=BINARY_WORKBENCH_DEFAULT_VERSION_NAME)
    mapper = InternalOffsetMapper(region)
    byte_overlays = internal_overlays_from_binary_overlays(
        mapper,
        parent.byte_overlays,
    )
    parent_byte_overlays = binary_overlays_from_internal_overlays(mapper, byte_overlays)
    preferences = seed_view_preferences(state, parent.view_preferences)
    return BinaryWorkbenchTabContextDTO(
        **{
            **parent.__dict__,
            "tab_id": uuid4().hex,
            "kind": BINARY_WORKBENCH_TAB_KIND.INTERNAL,
            "display_name": internal_file.name,
            "read_mode": "bytes",
            "reference_offsets": [
                name for name in parent.reference_offsets if name != "Binary"
            ],
            "reference_offset_bases": {
                name: value
                for name, value in parent.reference_offset_bases.items()
                if name != "Binary"
            },
            "internal_file_start_lba": internal_file.start_lba,
            "internal_parent_tab_id": parent.tab_id,
            "internal_parent_byte_overlays": parent_byte_overlays,
            "original_rows": [],
            "rows": [],
            "file_size": region.approximate_size,
            "original_file_size": 0,
            "versions": [version],
            "active_version_name": version.name,
            "workspace_path": None,
            "module_paths": {},
            "module_checksums": {},
            "version_dirty": False,
            "byte_overlays": byte_overlays,
            "instruction_overlays": {},
            "view_preferences": BinaryWorkbenchViewPreferencesDTO(
                visible_columns={
                    name: visible
                    for name, visible in preferences.visible_columns.items()
                    if name != "Binary"
                },
                decoded_text_tables=list(preferences.decoded_text_tables),
            ),
        }
    )
