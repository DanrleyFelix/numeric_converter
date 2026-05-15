from pathlib import Path

from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.repository.binary_workbench_workspace.constants import (
    ACTIVE_VERSION,
    ENCODING_TABLES,
    LBA_FILESYSTEM,
    MEMORY_REGIONS,
    MODULE_FOLDERS,
    SCHEMA_VERSION,
    SYMBOLS,
    VERSION_PATH_PREFIX,
    VERSIONS,
)
from src.presentation.repository.binary_workbench_workspace.payloads import (
    checksum,
    lba_payload,
    memory_regions_payload,
    source_payload,
    symbols_payload,
    version_payload,
)


def default_module_directories(directory: Path) -> dict[str, str]:
    return {key: str(directory / folder) for key, folder in MODULE_FOLDERS.items()}


def module_directories(manifest: dict[str, object], directory: Path) -> dict[str, str]:
    raw = manifest.get("module_directories")
    return {**default_module_directories(directory), **(raw if isinstance(raw, dict) else {})}


def module_paths(modules: dict[str, object], directory: Path) -> dict[str, str]:
    paths = {
        key: str(resolve_module_path(value, directory))
        for key in (SYMBOLS, LBA_FILESYSTEM, MEMORY_REGIONS)
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
            MEMORY_REGIONS: relative_module_path(Path(paths[MEMORY_REGIONS]), directory),
            VERSIONS: version_paths,
            ACTIVE_VERSION: tab.active_version_name,
            ENCODING_TABLES: None,
        },
        "module_directories": directories,
    }


def tab_checksums(tab: BinaryWorkbenchTabContextDTO) -> dict[str, str]:
    return checksums_for(
        tab.variables,
        tab.equates,
        tab.lba_sector_size,
        tab.internal_files,
        tab.memory_regions,
        tab.versions,
    )


def checksums_for(variables, equates, sector_size, files, regions, versions) -> dict[str, str]:
    return {
        SYMBOLS: checksum(symbols_payload("", variables, equates)),
        LBA_FILESYSTEM: checksum(lba_payload("", sector_size, files)),
        MEMORY_REGIONS: checksum(memory_regions_payload("", regions)),
        VERSIONS: checksum({"versions": [version_payload(item) for item in versions]}),
    }


def resolve_module_path(value: str, directory: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else directory / path


def relative_module_path(path: Path, directory: Path) -> str:
    try:
        return str(path.relative_to(directory))
    except ValueError:
        return str(path)
