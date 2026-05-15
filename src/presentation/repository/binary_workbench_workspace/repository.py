from __future__ import annotations

from pathlib import Path

from src.core.binary_workbench.file_ops import overlay_from_version_rows
from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
    labels_from_instruction_overlays,
)
from src.modules.dtos import BinaryWorkbenchTabContextDTO, BinaryWorkbenchVersionDTO
from src.modules.utils import read_json, write_json
from src.presentation.repository.binary_workbench_workspace.constants import (
    ACTIVE_VERSION,
    LBA_FILESYSTEM,
    MEMORY_REGIONS,
    MODULE_FOLDERS,
    MODULE_SUFFIXES,
    SCHEMA_VERSION,
    SYMBOLS,
    VERSION_PATH_PREFIX,
    VERSIONS,
    safe_stem,
)
from src.presentation.repository.binary_workbench_workspace.manifest import (
    checksums_for,
    default_module_directories,
    manifest_payload,
    module_directories,
    module_paths as module_paths_from_manifest,
    relative_module_path,
    resolve_module_path,
    tab_checksums,
)
from src.presentation.repository.binary_workbench_workspace.payloads import (
    lba_from_payload,
    lba_payload,
    memory_regions_from_payload,
    memory_regions_payload,
    source_matches,
    symbols_from_payload,
    symbols_payload,
    version_from_payload,
    version_payload,
)


class BinaryWorkbenchWorkspaceRepository:
    def __init__(self, root: Path) -> None:
        self._directory = (
            root
            if root.name == "workspaces" and root.parent.name == "data"
            else root / "data" / "workspaces"
        )
        self._directory.mkdir(parents=True, exist_ok=True)
        for folder in MODULE_FOLDERS.values():
            (self._directory / folder).mkdir(parents=True, exist_ok=True)
    @property
    def directory(self) -> Path:
        return self._directory
    def default_module_directories(self) -> dict[str, str]:
        return default_module_directories(self._directory)
    def find_for_source(self, path: Path) -> Path | None:
        for candidate in self._directory.glob("*.json"):
            payload = read_json(candidate)
            if payload and payload.get("schema_version") == SCHEMA_VERSION:
                if source_matches(payload.get("source"), path):
                    return candidate
        return None

    def load_tab_workspace(
        self,
        tab: BinaryWorkbenchTabContextDTO,
        path: Path,
    ) -> BinaryWorkbenchTabContextDTO:
        manifest = read_json(path)
        if not manifest or manifest.get("schema_version") != SCHEMA_VERSION:
            return tab
        modules = manifest.get("modules") if isinstance(manifest.get("modules"), dict) else {}
        directories = module_directories(manifest, self._directory)
        module_paths = module_paths_from_manifest(modules, self._directory)
        variables, equates = symbols_from_payload(read_json(Path(module_paths.get(SYMBOLS, ""))))
        sector_size, files = lba_from_payload(read_json(Path(module_paths.get(LBA_FILESYSTEM, ""))))
        regions = memory_regions_from_payload(read_json(Path(module_paths.get(MEMORY_REGIONS, ""))))
        versions = self._versions_from_manifest(modules)
        active = modules.get(ACTIVE_VERSION) if isinstance(modules.get(ACTIVE_VERSION), str) else None
        active_version = next((item for item in versions if item.name == active), None)
        active = active if active_version is not None else None
        overlays = dict(active_version.instruction_overlays) if active_version else dict(tab.instruction_overlays)
        byte_overlays = overlay_from_version_rows(active_version.rows) if active_version else {}
        byte_overlays.update(byte_overlays_from_instruction_overlays(overlays, variables, equates))
        labels = labels_from_instruction_overlays(overlays) or dict(tab.labels)
        checksums = checksums_for(variables, equates, sector_size, files, regions, versions)
        return BinaryWorkbenchTabContextDTO(
            **{
                **tab.__dict__,
                "variables": variables,
                "equates": equates,
                "internal_files": files,
                "lba_sector_size": sector_size,
                "memory_regions": regions,
                "versions": versions,
                "active_version_name": active,
                "instruction_overlays": overlays,
                "byte_overlays": byte_overlays or dict(tab.byte_overlays),
                "labels": labels,
                "workspace_path": str(path),
                "module_paths": module_paths,
                "module_directories": directories,
                "module_checksums": checksums,
            }
        )

    def save_tab_workspace(
        self,
        tab: BinaryWorkbenchTabContextDTO,
        path: Path | None = None,
    ) -> BinaryWorkbenchTabContextDTO:
        target = self._normalize_manifest_path(path or Path(tab.workspace_path or self._default_manifest(tab)))
        target.parent.mkdir(parents=True, exist_ok=True)
        directories = {**self.default_module_directories(), **tab.module_directories}
        module_paths = dict(tab.module_paths)
        stem = safe_stem(target.stem)
        module_paths[SYMBOLS] = str(self._write_module(directories, module_paths, SYMBOLS, stem, symbols_payload(stem, tab.variables, tab.equates)))
        module_paths[LBA_FILESYSTEM] = str(self._write_module(directories, module_paths, LBA_FILESYSTEM, stem, lba_payload(stem, tab.lba_sector_size, tab.internal_files)))
        module_paths[MEMORY_REGIONS] = str(self._write_module(directories, module_paths, MEMORY_REGIONS, stem, memory_regions_payload(stem, tab.memory_regions)))
        version_paths = self._write_versions(tab, directories, module_paths, stem)
        manifest = manifest_payload(tab, self._directory, module_paths, version_paths, directories)
        write_json(target, manifest)
        checksums = tab_checksums(tab)
        return BinaryWorkbenchTabContextDTO(
            **{**tab.__dict__, "workspace_path": str(target), "module_paths": module_paths, "module_directories": directories, "module_checksums": checksums}
        )

    def checksums_for_tab(self, tab: BinaryWorkbenchTabContextDTO) -> dict[str, str]:
        return tab_checksums(tab)
    def _default_manifest(self, tab: BinaryWorkbenchTabContextDTO) -> Path:
        return self._directory / f"{safe_stem(tab.display_name)}.json"
    def _normalize_manifest_path(self, path: Path) -> Path:
        target = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
        return target if target.is_absolute() and self._directory in target.parents else self._directory / target.name
    def _write_module(self, directories: dict[str, str], paths: dict[str, str], key: str, stem: str, payload: dict[str, object]) -> Path:
        target = Path(paths.get(key) or Path(directories[key]) / f"{stem}_{MODULE_SUFFIXES[key]}.json")
        return write_json(target, payload)

    def _write_versions(self, tab: BinaryWorkbenchTabContextDTO, directories: dict[str, str], paths: dict[str, str], stem: str) -> dict[str, str]:
        version_paths: dict[str, str] = {}
        for version in tab.versions:
            key = f"{VERSION_PATH_PREFIX}{version.name}"
            target = Path(paths.get(key) or Path(directories[VERSIONS]) / f"{stem}_{safe_stem(version.name)}.json")
            write_json(target, version_payload(version))
            paths[key] = str(target)
            version_paths[version.name] = relative_module_path(target, self._directory)
        return version_paths

    def _versions_from_manifest(self, modules: dict[str, object]) -> list[BinaryWorkbenchVersionDTO]:
        raw = modules.get(VERSIONS)
        if not isinstance(raw, dict):
            return []
        versions = [version_from_payload(read_json(resolve_module_path(value, self._directory)), str(name)) for name, value in raw.items() if isinstance(value, str)]
        return [item for item in versions if item is not None]
