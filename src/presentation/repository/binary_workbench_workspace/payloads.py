from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.modules.dtos import (
    BinaryWorkbenchInternalFileDTO,
    BinaryWorkbenchMemoryRegionDTO,
    BinaryWorkbenchVersionDTO,
)
from src.modules.utils import normalize_string_map
from src.presentation.repository.binary_workbench_payload import (
    _instruction_overlays,
    _internal_files,
    _memory_regions,
    _rows,
)
from src.core.binary_workbench.version_overlays import instruction_overlays_from_rows
from src.core.binary_workbench.resource_identity import file_resource_identifiers


def checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def source_payload(path: Path) -> dict[str, str]:
    resolved = path.resolve()
    return {
        "directory": str(resolved.parent),
        "filename": resolved.name,
        "identifier": file_resource_identifiers(resolved)[0],
    }


def source_matches(payload: object, path: Path) -> bool:
    if not isinstance(payload, dict):
        return False
    current = source_payload(path)
    return (
        str(payload.get("directory", "")).lower() == current["directory"].lower()
        and str(payload.get("filename", "")).lower() == current["filename"].lower()
    )


def symbols_payload(name: str, variables: dict[str, str], equates: dict[str, str]) -> dict[str, object]:
    return {"name": name, "variables": dict(variables), "equates": dict(equates)}


def lba_payload(
    name: str,
    sector_size: int,
    files: list[BinaryWorkbenchInternalFileDTO],
) -> dict[str, object]:
    return {
        "name": name,
        "sector_size": sector_size,
        "internal_files": [{"name": item.name, "start_lba": item.start_lba} for item in files],
    }


def memory_regions_payload(
    name: str,
    regions: list[BinaryWorkbenchMemoryRegionDTO],
) -> dict[str, object]:
    return {
        "name": name,
        "regions": [
            {
                "name": item.name,
                "start_offset": item.start_offset,
                "end_offset": item.end_offset,
            }
            for item in regions
        ],
    }


def version_payload(version: BinaryWorkbenchVersionDTO) -> dict[str, object]:
    overlays = version.instruction_overlays or {
        row.offsets.get("File", "0x00000000"): row.instruction
        for row in version.rows
        if row.instruction
    }
    return {
        "name": version.name,
        "instructions": {
            offset: instruction for offset, instruction in sorted(overlays.items())
        },
    }


def symbols_from_payload(payload: dict[str, object] | None) -> tuple[dict[str, str], dict[str, str]]:
    if not isinstance(payload, dict):
        return {}, {}
    return normalize_string_map(payload.get("variables")), normalize_string_map(payload.get("equates"))


def lba_from_payload(payload: dict[str, object] | None) -> tuple[int, list[BinaryWorkbenchInternalFileDTO]]:
    if not isinstance(payload, dict):
        return 2352, []
    sector_size = payload.get("sector_size")
    size = sector_size if isinstance(sector_size, int) and sector_size in {2048, 2334, 2352} else 2352
    return size, _internal_files(payload.get("internal_files"))


def memory_regions_from_payload(payload: dict[str, object] | None) -> list[BinaryWorkbenchMemoryRegionDTO]:
    if not isinstance(payload, dict):
        return []
    return _memory_regions(payload.get("regions"))


def version_from_payload(
    payload: dict[str, object] | None,
    fallback_name: str,
) -> BinaryWorkbenchVersionDTO | None:
    if not isinstance(payload, dict):
        return None
    name = payload.get("name")
    overlays = _instruction_overlays(payload.get("instructions"))
    if not overlays:
        overlays = _instruction_overlays(payload.get("instruction_overlays"))
    if not overlays:
        overlays = instruction_overlays_from_rows(rows := _rows(payload.get("rows")))
    else:
        rows = _rows(payload.get("rows"))
    version_name = name if isinstance(name, str) and name else fallback_name
    return BinaryWorkbenchVersionDTO(
        name=version_name,
        rows=rows,
        instruction_overlays=overlays,
    )
