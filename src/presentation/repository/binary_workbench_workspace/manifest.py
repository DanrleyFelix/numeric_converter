from pathlib import Path

from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchViewPreferencesDTO
from src.presentation.repository.binary_workbench_workspace.constants import (
    ACTIVE_VERSION,
    COMMANDS,
    ENCODING_TABLES,
    LBA_FILESYSTEM,
    MODULE_FOLDERS,
    SCHEMA_VERSION,
    SYMBOLS,
    OFFSET_REGIONS,
    VIEW_PREFERENCES,
    VERSION_PATH_PREFIX,
    VERSIONS,
)
from src.presentation.repository.binary_workbench_workspace.payloads import (
    commands_payload,
    checksum,
    encoding_tables_payload,
    lba_payload,
    offset_regions_payload,
    source_payload,
    symbols_payload,
    view_preferences_payload,
    version_payload,
)


def default_module_directories(directory: Path) -> dict[str, str]:
    return {key: str(directory / folder) for key, folder in MODULE_FOLDERS.items()}


def module_directories(manifest: dict[str, object], directory: Path) -> dict[str, str]:
    raw = manifest.get("module_directories")
    values = {**default_module_directories(directory), **(raw if isinstance(raw, dict) else {})}
    return {key: str(values[key]) for key in MODULE_FOLDERS if key in values}


def module_paths(modules: dict[str, object], directory: Path) -> dict[str, str]:
    paths = {
        key: str(resolve_module_path(value, directory))
        for key in (SYMBOLS, LBA_FILESYSTEM, COMMANDS, ENCODING_TABLES, OFFSET_REGIONS)
        if isinstance((value := modules.get(key)), str)
    }
    raw_versions = modules.get(VERSIONS) if isinstance(modules.get(VERSIONS), dict) else {}
    for name, value in raw_versions.items():
        if isinstance(value, str):
            paths[f"{VERSION_PATH_PREFIX}{name}"] = str(resolve_module_path(value, directory))
    return paths


def manifest_payload(
    tab: BinaryWorkbenchTabContextDTO,
    directory: Path,
    paths: dict[str, str],
    version_paths: dict[str, str],
    directories: dict[str, str],
) -> dict[str, object]:
    source = source_payload(Path(tab.source_path)) if tab.source_path else {"directory": "", "filename": tab.display_name}
    return {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "modules": {
            SYMBOLS: relative_module_path(Path(paths[SYMBOLS]), directory),
            LBA_FILESYSTEM: relative_module_path(Path(paths[LBA_FILESYSTEM]), directory),
            COMMANDS: relative_module_path(Path(paths[COMMANDS]), directory),
            VERSIONS: version_paths,
            ACTIVE_VERSION: tab.active_version_name,
            ENCODING_TABLES: relative_module_path(Path(paths[ENCODING_TABLES]), directory),
            OFFSET_REGIONS: relative_module_path(Path(paths[OFFSET_REGIONS]), directory),
        },
        "module_directories": directories,
        VIEW_PREFERENCES: view_preferences_payload(tab.view_preferences),
    }


def tab_checksums(tab: BinaryWorkbenchTabContextDTO) -> dict[str, str]:
    return checksums_for(
        tab.variables,
        tab.equates,
        tab.lba_sector_size,
        tab.internal_files,
        tab.versions,
        tab.custom_commands,
        tab.encoding_tables,
        tab.offset_regions,
        tab.view_preferences,
    )


def checksums_for(
    variables,
    equates,
    sector_size,
    files,
    versions,
    commands,
    encoding_tables=(),
    offset_regions=(),
    view_preferences=None,
) -> dict[str, str]:
    view_preferences = view_preferences or BinaryWorkbenchViewPreferencesDTO()
    return {
        SYMBOLS: checksum(symbols_payload("", variables, equates)),
        LBA_FILESYSTEM: checksum(lba_payload("", sector_size, files)),
        VERSIONS: checksum({"versions": [version_payload(item) for item in versions]}),
        COMMANDS: checksum(commands_payload("", commands)),
        ENCODING_TABLES: checksum(encoding_tables_payload("", list(encoding_tables))),
        OFFSET_REGIONS: checksum(offset_regions_payload("", list(offset_regions))),
        VIEW_PREFERENCES: checksum(view_preferences_payload(view_preferences)),
    }


def resolve_module_path(value: str, directory: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else directory / path


def relative_module_path(path: Path, directory: Path) -> str:
    try:
        return str(path.relative_to(directory))
    except ValueError:
        return str(path)
