from __future__ import annotations

from uuid import uuid4

from src.core.binary_workbench.internal_file_region import InternalFileRegion
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_BINARY_OFFSET_COLUMN,
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
from src.presentation.repository.binary_workbench_workspace.constants import (
    VERSION_PATH_PREFIX,
    VERSIONS,
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
    reference_offsets = list(parent.reference_offsets)
    if BINARY_WORKBENCH_BINARY_OFFSET_COLUMN not in reference_offsets:
        reference_offsets.append(BINARY_WORKBENCH_BINARY_OFFSET_COLUMN)
    preferences = seed_view_preferences(state, parent.view_preferences)
    view_preferences = BinaryWorkbenchViewPreferencesDTO(
        visible_columns={
            **preferences.visible_columns,
            BINARY_WORKBENCH_BINARY_OFFSET_COLUMN: False,
        },
        decoded_text_tables=list(preferences.decoded_text_tables),
    )
    return BinaryWorkbenchTabContextDTO(
        **{
            **parent.__dict__,
            "tab_id": uuid4().hex,
            "kind": BINARY_WORKBENCH_TAB_KIND.INTERNAL,
            "display_name": internal_file.name,
            "read_mode": "bytes",
            "reference_offsets": reference_offsets,
            "reference_offset_bases": {
                **parent.reference_offset_bases,
                BINARY_WORKBENCH_BINARY_OFFSET_COLUMN: "0x00000000",
            },
            "internal_file_start_lba": internal_file.start_lba,
            "original_rows": [],
            "rows": [],
            "file_size": region.approximate_size,
            "original_file_size": 0,
            "versions": [version],
            "active_version_name": version.name,
            "workspace_path": None,
            "module_paths": {
                key: value
                for key, value in parent.module_paths.items()
                if key != VERSIONS and not key.startswith(VERSION_PATH_PREFIX)
            },
            "module_checksums": {},
            "version_dirty": False,
            "byte_overlays": {},
            "instruction_overlays": {},
            "view_preferences": view_preferences,
        }
    )
