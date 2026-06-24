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
    COMMANDS,
    ENCODING_TABLES,
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
    commands_from_payload,
    commands_payload,
    encoding_tables_from_payload,
    encoding_tables_payload,
    lba_from_payload,
    lba_payload,
    offset_regions_from_payload,
    offset_regions_payload,
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
    def find_for_source(self, path: Path, preferred: Path | None = None) -> Path | None:
        if preferred is not None and preferred.exists():
            payload = read_json(preferred)
            if payload and payload.get("schema_version") == SCHEMA_VERSION:
                if source_matches(payload.get("source"), path):
                    return preferred
        matches: list[Path] = []
        for candidate in self._directory.glob("*.json"):
            payload = read_json(candidate)
            if payload and payload.get("schema_version") == SCHEMA_VERSION:
                if source_matches(payload.get("source"), path):
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
        variables, equates = symbols_from_payload(read_json(Path(module_paths.get(SYMBOLS, ""))))
        sector_size, files = lba_from_payload(read_json(Path(module_paths.get(LBA_FILESYSTEM, ""))))
        custom_commands = commands_from_payload(read_json(Path(module_paths.get(COMMANDS, ""))))
        encoding_tables = encoding_tables_from_payload(read_json(Path(module_paths.get(ENCODING_TABLES, ""))))
        offset_regions = offset_regions_from_payload(read_json(Path(module_paths.get(OFFSET_REGIONS, ""))))
        view_preferences = view_preferences_from_payload(
            manifest.get("view_preferences"),
            tab.view_preferences,
        )
        versions = self._versions_from_manifest(modules)
        active = modules.get(ACTIVE_VERSION) if isinstance(modules.get(ACTIVE_VERSION), str) else None
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
                "custom_commands": custom_commands,
                "internal_files": files,
                "lba_sector_size": sector_size,
                "encoding_tables": encoding_tables,
                "offset_regions": offset_regions,
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
                    loaded.custom_commands,
                    loaded.encoding_tables,
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
        module_paths[SYMBOLS] = str(self._write_module(directories, module_paths, SYMBOLS, stem, symbols_payload(stem, tab.variables, tab.equates)))
        module_paths[LBA_FILESYSTEM] = str(self._write_module(directories, module_paths, LBA_FILESYSTEM, stem, lba_payload(stem, tab.lba_sector_size, tab.internal_files)))
        module_paths[COMMANDS] = str(self._write_module(directories, module_paths, COMMANDS, stem, commands_payload(stem, tab.custom_commands)))
        module_paths[ENCODING_TABLES] = str(self._write_module(directories, module_paths, ENCODING_TABLES, stem, encoding_tables_payload(stem, tab.encoding_tables)))
        module_paths[OFFSET_REGIONS] = str(self._write_module(directories, module_paths, OFFSET_REGIONS, stem, offset_regions_payload(stem, tab.offset_regions)))
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

    def load_versions_file(self, path: Path) -> list[BinaryWorkbenchVersionDTO]:
        return versions_from_payload(read_json(path))

    def _default_manifest(self, tab: BinaryWorkbenchTabContextDTO) -> Path:
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
        write_json(target, versions_payload(tab.versions, tab.active_version_name))
        paths[VERSIONS] = str(target)
        for version in tab.versions:
            paths[f"{VERSION_PATH_PREFIX}{version.name}"] = str(target)
        return {
            version.name: relative_module_path(target, self._directory)
            for version in tab.versions
        }

    def _versions_from_manifest(self, modules: dict[str, object]) -> list[BinaryWorkbenchVersionDTO]:
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
            loaded = versions_from_payload(read_json(path))
            if loaded:
                versions.extend(loaded)
                continue
            version = version_from_payload(read_json(path), str(name))
            if version is not None:
                versions.append(version)
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
