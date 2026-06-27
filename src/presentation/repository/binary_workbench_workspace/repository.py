from __future__ import annotations

from pathlib import Path

from src.core.binary_workbench.context_overlays import compact_binary_context_overlays
from src.core.binary_workbench.file_ops import overlay_from_version_rows
from src.core.binary_workbench.legacy_overlays import discard_legacy_nop_overlays
from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
    labels_from_instruction_overlays,
    without_blank_instruction_overlays,
)
from src.core.binary_workbench.version_line_comments import apply_line_comments
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO, BinaryWorkbenchTabContextDTO, BinaryWorkbenchVersionDTO
from src.modules.utils import read_json, write_json
from src.presentation.repository.binary_workbench_workspace.constants import (
    ACTIVE_VERSION,
    LBA_FILESYSTEM,
    MODULE_FOLDERS,
    MODULE_SUFFIXES,
    SCHEMA_VERSION,
    OFFSET_REGIONS,
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
    offset_region_details_from_payload,
    offset_regions_from_payload,
    offset_regions_payload,
    offset_regions_payload_preserving_details,
    source_matches,
    symbols_from_payload,
    symbols_payload,
    version_from_payload,
    versions_from_payload,
    versions_payload,
    view_preferences_from_payload,
)


class BinaryWorkbenchWorkspaceRepository:
    def __init__(self, root: Path) -> None:
        self._directory = (
            root
            if root.name == "workspaces"
            else root / "data" / "binary_workbench" / "workspaces"
        )
        self._directory.mkdir(parents=True, exist_ok=True)
        for folder in MODULE_FOLDERS.values():
            (self._directory / folder).mkdir(parents=True, exist_ok=True)
        self._decoded_tables_directory = self._directory.parent / "decoded_tables"
        self._decoded_tables_directory.mkdir(parents=True, exist_ok=True)
    @property
    def directory(self) -> Path:
        return self._directory
    def default_module_directories(self) -> dict[str, str]:
        return default_module_directories(self._directory)
    @property
    def decoded_tables_directory(self) -> Path:
        return self._decoded_tables_directory
    def find_for_source(
        self,
        path: Path,
        preferred: Path | None = None,
        internal_file_start_lba: int | None = None,
    ) -> Path | None:
        if preferred is not None and preferred.exists():
            payload = read_json(preferred)
            if payload and payload.get("schema_version") == SCHEMA_VERSION:
                if source_matches(payload.get("source"), path, internal_file_start_lba):
                    return preferred
        matches: list[Path] = []
        for candidate in self._directory.glob("*.json"):
            payload = read_json(candidate)
            if payload and payload.get("schema_version") == SCHEMA_VERSION:
                if source_matches(payload.get("source"), path, internal_file_start_lba):
                    matches.append(candidate)
        return matches[0] if len(matches) == 1 else None

    def load_tab_workspace(
        self,
        tab: BinaryWorkbenchTabContextDTO,
        path: Path,
    ) -> BinaryWorkbenchTabContextDTO:
        tab = discard_legacy_nop_overlays(compact_binary_context_overlays(tab))
        manifest = read_json(path)
        if not manifest or manifest.get("schema_version") != SCHEMA_VERSION:
            return tab
        modules = manifest.get("modules") if isinstance(manifest.get("modules"), dict) else {}
        directories = module_directories(manifest, self._directory)
        module_paths = module_paths_from_manifest(modules, self._directory)
        if _manifest_internal_file_start_lba(manifest) is not None:
            module_paths = _module_paths_for_manifest(module_paths, path)
        variables, equates = symbols_from_payload(read_json(Path(module_paths.get(SYMBOLS, ""))))
        sector_size, files = lba_from_payload(read_json(Path(module_paths.get(LBA_FILESYSTEM, ""))))
        if tab.internal_file_start_lba is not None and not files:
            sector_size = tab.lba_sector_size
            files = list(tab.internal_files)
        offset_regions: list = []
        view_preferences = view_preferences_from_payload(
            manifest.get("view_preferences"),
            tab.view_preferences,
        )
        active = modules.get(ACTIVE_VERSION) if isinstance(modules.get(ACTIVE_VERSION), str) else None
        versions = self._versions_from_manifest(modules, active)
        active_version = next((item for item in versions if item.name == active), None)
        active = active if active_version is not None else None
        if not versions:
            versions = list(tab.versions)
            active = tab.active_version_name
            active_version = next((item for item in versions if item.name == active), None)
        tab_byte_overlays, tab_instruction_overlays = without_blank_instruction_overlays(
            dict(tab.byte_overlays),
            dict(tab.instruction_overlays),
        )
        rows = (
            self._version_rows(tab, active_version)
            if active_version and active_version.instructions_by_line
            else tab.rows
        )
        overlays = (
            self._instruction_overlays_for_version(tab, active_version)
            if active_version
            else tab_instruction_overlays
        )
        byte_overlays = overlay_from_version_rows(active_version.rows) if active_version else {}
        byte_overlays.update(byte_overlays_from_instruction_overlays(overlays, variables, equates))
        byte_overlays, overlays = without_blank_instruction_overlays(byte_overlays, overlays)
        labels = labels_from_instruction_overlays(overlays) or dict(tab.labels)
        loaded = discard_legacy_nop_overlays(compact_binary_context_overlays(BinaryWorkbenchTabContextDTO(
            **{
                **tab.__dict__,
                "variables": variables,
                "equates": equates,
                "internal_files": files,
                "lba_sector_size": sector_size,
                "offset_regions": offset_regions,
                "offset_regions_loaded": False,
                "view_preferences": view_preferences,
                "versions": versions,
                "active_version_name": active,
                "read_mode": "assembly"
                if active_version and active_version.instructions_by_line
                else tab.read_mode,
                "rows": rows,
                "instruction_overlays": overlays,
                "byte_overlays": byte_overlays or tab_byte_overlays,
                "labels": labels,
                "workspace_path": str(path),
                "module_paths": module_paths,
                "module_directories": directories,
            }
        )))
        return BinaryWorkbenchTabContextDTO(
            **{
                **loaded.__dict__,
                "module_checksums": checksums_for(
                    variables,
                    equates,
                    sector_size,
                    files,
                    loaded.versions,
                    loaded.offset_regions,
                    loaded.view_preferences,
                ),
            }
        )

    def save_tab_workspace(
        self,
        tab: BinaryWorkbenchTabContextDTO,
        path: Path | None = None,
    ) -> BinaryWorkbenchTabContextDTO:
        tab = compact_binary_context_overlays(tab)
        target = self._normalize_manifest_path(path or Path(tab.workspace_path or self._default_manifest(tab)))
        target.parent.mkdir(parents=True, exist_ok=True)
        directories = {
            key: value
            for key, value in {**self.default_module_directories(), **tab.module_directories}.items()
            if key in MODULE_FOLDERS
        }
        module_paths = {key: value for key, value in tab.module_paths.items() if key in MODULE_FOLDERS}
        stem = safe_stem(target.stem)
        if tab.internal_file_start_lba is not None:
            module_paths = _module_paths_for_internal_save(module_paths, stem)
        module_paths[SYMBOLS] = str(self._write_module(directories, module_paths, SYMBOLS, stem, symbols_payload(stem, tab.variables, tab.equates)))
        module_paths[LBA_FILESYSTEM] = str(self._write_module(directories, module_paths, LBA_FILESYSTEM, stem, lba_payload(stem, tab.lba_sector_size, tab.internal_files)))
        if tab.offset_regions_loaded or OFFSET_REGIONS not in module_paths:
            existing = read_json(Path(module_paths.get(OFFSET_REGIONS, "")))
            module_paths[OFFSET_REGIONS] = str(self._write_module(
                directories,
                module_paths,
                OFFSET_REGIONS,
                stem,
                offset_regions_payload_preserving_details(stem, tab.offset_regions, existing),
            ))
        version_paths = self._write_versions(tab, directories, module_paths, stem)
        manifest = manifest_payload(tab, self._directory, module_paths, version_paths, directories)
        write_json(target, manifest)
        checksums = tab_checksums(tab)
        return BinaryWorkbenchTabContextDTO(
            **{
                **tab.__dict__,
                "workspace_path": str(target),
                "module_paths": module_paths,
                "module_directories": directories,
                "module_checksums": checksums,
                "version_dirty": False,
            }
        )

    def checksums_for_tab(self, tab: BinaryWorkbenchTabContextDTO) -> dict[str, str]:
        return tab_checksums(tab)

    def load_offset_regions_file(self, path: Path) -> list:
        return offset_regions_from_payload(read_json(path), include_details=False)

    def load_offset_region_details(self, path: Path, name: str, offset: int) -> str:
        return offset_region_details_from_payload(read_json(path), name, offset)

    def load_versions_file(self, path: Path) -> list[BinaryWorkbenchVersionDTO]:
        return versions_from_payload(read_json(path))

    def load_version_from_context(
        self,
        tab: BinaryWorkbenchTabContextDTO,
        name: str,
    ) -> BinaryWorkbenchVersionDTO | None:
        paths = dict(tab.module_paths)
        path = paths.get(f"{VERSION_PATH_PREFIX}{name}") or paths.get(VERSIONS)
        if not path:
            return None
        return _version_named(read_json(Path(path)), name)

    def _default_manifest(self, tab: BinaryWorkbenchTabContextDTO) -> Path:
        if tab.source_path and tab.internal_file_start_lba is not None:
            source_stem = safe_stem(Path(tab.source_path).stem)
            internal_stem = safe_stem(_internal_file_name(tab) or tab.display_name)
            return self._directory / f"{source_stem}_{internal_stem}_{tab.internal_file_start_lba:X}_workspace_manifest.json"
        if tab.source_path:
            return self._directory / f"{safe_stem(Path(tab.source_path).name)}_workspace_manifest.json"
        return self._directory / f"{safe_stem(tab.display_name)}_workspace_manifest.json"
    def _normalize_manifest_path(self, path: Path) -> Path:
        target = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
        return target if target.is_absolute() and self._directory in target.parents else self._directory / target.name
    def _write_module(self, directories: dict[str, str], paths: dict[str, str], key: str, stem: str, payload: dict[str, object]) -> Path:
        target = Path(paths.get(key) or Path(directories[key]) / f"{stem}_{MODULE_SUFFIXES[key]}.json")
        return write_json(target, payload)

    def _write_versions(self, tab: BinaryWorkbenchTabContextDTO, directories: dict[str, str], paths: dict[str, str], stem: str) -> dict[str, str]:
        if not tab.versions:
            return {}
        target = self._version_file_path(tab, paths, directories, stem)
        existing = read_json(target)
        existing_versions = existing.get("versions") if isinstance(existing, dict) else {}
        existing_versions = dict(existing_versions) if isinstance(existing_versions, dict) else {}
        loaded_versions = [version for version in tab.versions if not _version_placeholder(version, tab.active_version_name)]
        payload = versions_payload(loaded_versions, tab.active_version_name)
        merged_versions = {**existing_versions, **payload.get("versions", {})}
        for version in tab.versions:
            merged_versions.setdefault(version.name, {})
        write_json(target, {"active_version": tab.active_version_name, "versions": merged_versions})
        paths[VERSIONS] = str(target)
        for version in tab.versions:
            paths[f"{VERSION_PATH_PREFIX}{version.name}"] = str(target)
        return {
            version.name: relative_module_path(target, self._directory)
            for version in tab.versions
        }

    def _versions_from_manifest(
        self,
        modules: dict[str, object],
        active: str | None,
    ) -> list[BinaryWorkbenchVersionDTO]:
        raw = modules.get(VERSIONS)
        if not isinstance(raw, dict):
            return []
        versions: list[BinaryWorkbenchVersionDTO] = []
        seen_paths: set[Path] = set()
        for name, value in raw.items():
            if not isinstance(value, str):
                continue
            path = resolve_module_path(value, self._directory)
            if path in seen_paths:
                continue
            seen_paths.add(path)
            payload = read_json(path)
            loaded = _versions_with_only_active(payload, active)
            if loaded:
                versions.extend(loaded)
                continue
            version = version_from_payload(payload, str(name))
            if version is not None:
                versions.append(version if version.name == active else BinaryWorkbenchVersionDTO(name=version.name))
        return versions

    def _version_file_path(
        self,
        tab: BinaryWorkbenchTabContextDTO,
        paths: dict[str, str],
        directories: dict[str, str],
        stem: str,
    ) -> Path:
        active_key = f"{VERSION_PATH_PREFIX}{tab.active_version_name or ''}"
        existing = paths.get(VERSIONS) or paths.get(active_key)
        return Path(existing or Path(directories[VERSIONS]) / f"{stem}_versions.json")

    def _version_rows(
        self,
        tab: BinaryWorkbenchTabContextDTO,
        version: BinaryWorkbenchVersionDTO,
    ):
        rows = _apply_instruction_overlays(tab.original_rows or tab.rows, version.instruction_overlays)
        return apply_line_comments(rows, version.instructions_by_line, list(tab.reference_offsets))

    def _instruction_overlays_for_version(
        self,
        tab: BinaryWorkbenchTabContextDTO,
        version: BinaryWorkbenchVersionDTO,
    ) -> dict[str, str]:
        if version.instructions_by_line:
            return {
                **version.instruction_overlays,
                **{
                    row.offsets.get("File", "0x00000000"): row.instruction
                    for row in self._version_rows(tab, version)
                    if row.instruction and row.offsets.get("File") != "-"
                },
            }
        return dict(version.instruction_overlays)


def _apply_instruction_overlays(
    rows: list[BinaryWorkbenchRowDTO],
    overlays: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    return [
        BinaryWorkbenchRowDTO(
            offsets=row.offsets,
            instruction=overlays.get(row.offsets.get("File", "-"), row.instruction),
            bytes_text=row.bytes_text,
            original_instruction=row.original_instruction,
            original_bytes_text=row.original_bytes_text,
        )
        for row in rows
    ]


def _version_placeholder(version: BinaryWorkbenchVersionDTO, active: str | None) -> bool:
    return (
        version.name != active
        and not version.rows
        and not version.instruction_overlays
        and not version.instructions_by_line
    )


def _versions_with_only_active(
    payload: dict[str, object] | None,
    active: str | None,
) -> list[BinaryWorkbenchVersionDTO]:
    if not isinstance(payload, dict) or not isinstance(payload.get("versions"), dict):
        return []
    versions: list[BinaryWorkbenchVersionDTO] = []
    for name, raw in payload["versions"].items():
        if not isinstance(name, str) or not isinstance(raw, dict):
            continue
        if name == active:
            version = _version_named(payload, name)
            versions.append(version if version is not None else BinaryWorkbenchVersionDTO(name=name))
            continue
        versions.append(BinaryWorkbenchVersionDTO(name=name))
    return sorted(versions, key=lambda version: version.name != active)


def _version_named(
    payload: dict[str, object] | None,
    name: str,
) -> BinaryWorkbenchVersionDTO | None:
    if not isinstance(payload, dict):
        return None
    raw_versions = payload.get("versions")
    if isinstance(raw_versions, dict):
        raw = raw_versions.get(name)
        if not isinstance(raw, dict):
            return None
        instructions = raw.get("instructions")
        instructions = instructions if isinstance(instructions, dict) else raw
        return version_from_payload(
            {"name": name, "instructions": instructions, "rows": raw.get("rows")},
            name,
        )
    version = version_from_payload(payload, name)
    return version if version is not None and version.name == name else None


def _manifest_internal_file_start_lba(manifest: dict[str, object]) -> int | None:
    source = manifest.get("source")
    if not isinstance(source, dict):
        return None
    value = source.get("internal_file_start_lba")
    return value if isinstance(value, int) else None


def _module_paths_for_manifest(
    module_paths: dict[str, str],
    manifest_path: Path,
) -> dict[str, str]:
    stem = safe_stem(manifest_path.stem)
    return {
        key: value
        for key, value in module_paths.items()
        if _module_path_matches_workspace_stem(value, stem)
    }


def _module_paths_for_internal_save(
    module_paths: dict[str, str],
    stem: str,
) -> dict[str, str]:
    return {
        key: value
        for key, value in module_paths.items()
        if _module_path_matches_workspace_stem(value, stem)
    }


def _module_path_matches_workspace_stem(value: str, stem: str) -> bool:
    path_stem = safe_stem(Path(value).stem)
    return path_stem == stem or path_stem.startswith(f"{stem}_")


def _internal_file_name(tab: BinaryWorkbenchTabContextDTO) -> str:
    for item in tab.internal_files:
        if item.start_lba == tab.internal_file_start_lba:
            return item.name
    return ""
