from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from uuid import uuid4

from src.core.binary_workbench.symbols.compatibility.legacy import (
    LegacySymbolsPayloadAdapter,
    definitions_payload,
)
from src.core.binary_workbench.symbols.definitions import SymbolScope
from src.modules.utils import read_json, write_json

SYMBOL_SCHEMA_VERSION = 3


@dataclass(frozen=True, slots=True)
class SymbolMigrationReport:
    """Describe a safe legacy-to-modern migration attempt."""

    success: bool
    migrated_tabs: tuple[str, ...] = ()
    pending_tabs: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    error: str | None = None


@dataclass(slots=True)
class LazyTabDescriptor:
    """Keep inactive tab payloads opaque until a real consumer requests them."""

    tab_id: str
    payload_version: int
    raw_payload: dict[str, object]
    global_revision_watermark: int = 0
    pending_symbol_patches: tuple[dict[str, object], ...] = ()
    migration_pending: bool = True


class SymbolSchemaMigrator:
    """Upgrade only loaded scopes and preserve inactive tab payloads verbatim."""

    def migrate_payload(
        self,
        payload: dict[str, object],
        active_tab_id: str | None,
    ) -> tuple[dict[str, object], SymbolMigrationReport]:
        """Migrate globals and the active tab without materializing other tabs."""

        workspace_id = str(payload.get("workspace_id") or uuid4())
        adapter = LegacySymbolsPayloadAdapter(workspace_id)
        output = dict(payload)
        global_result = adapter.adapt(
            payload,
            SymbolScope.GLOBAL,
            modern_key="global_symbol_definitions",
        )
        output["schema_version"] = SYMBOL_SCHEMA_VERSION
        output["workspace_id"] = workspace_id
        output["global_symbol_definitions"] = definitions_payload(global_result.definitions)
        output["global_symbols"] = {item.name: item.value for item in global_result.definitions}
        tabs: list[object] = []
        migrated: list[str] = []
        pending: list[str] = []
        conflicts: list[str] = list(global_result.conflicts)
        for raw in payload.get("tabs", []) if isinstance(payload.get("tabs"), list) else []:
            if not isinstance(raw, dict):
                continue
            tab_id = str(raw.get("tab_id", ""))
            if tab_id != active_tab_id:
                tabs.append(dict(raw))
                pending.append(tab_id)
                continue
            adapted = adapter.adapt(raw, SymbolScope.LOCAL, tab_id)
            conflicts.extend(f"Tab '{tab_id}': {item}" for item in adapted.conflicts)
            tab = dict(raw)
            tab["symbol_definitions"] = definitions_payload(adapted.definitions)
            tab["symbols"] = {item.name: item.value for item in adapted.definitions}
            tab.pop("variables", None)
            tab.pop("equates", None)
            tab.pop("symbol_offsets", None)
            tabs.append(tab)
            migrated.append(tab_id)
        output["tabs"] = tabs
        return output, SymbolMigrationReport(
            True,
            tuple(migrated),
            tuple(pending),
            tuple(conflicts),
        )

    def migrate_file(self, path: Path, active_tab_id: str | None) -> SymbolMigrationReport:
        """Validate, back up, and atomically replace one legacy JSON file."""

        original = read_json(path)
        if not isinstance(original, dict):
            return SymbolMigrationReport(False, error="The Symbols payload is not valid JSON.")
        migrated, report = self.migrate_payload(original, active_tab_id)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.migration.json")
        try:
            write_json(temporary, migrated)
            if read_json(temporary) != migrated:
                return SymbolMigrationReport(False, error="The migrated payload could not be validated.")
            copy2(path, path.with_suffix(path.suffix + ".v2.bak"))
            temporary.replace(path)
            return report
        except OSError as error:
            return SymbolMigrationReport(False, error=str(error))
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
