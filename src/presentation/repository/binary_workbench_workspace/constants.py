from __future__ import annotations

from pathlib import Path

SCHEMA_VERSION = 2
SYMBOLS = "symbols"
LBA_FILESYSTEM = "lba_filesystem"
VERSIONS = "versions"
ENCODING_TABLES = "encoding_tables"
ACTIVE_VERSION = "active_version"

MODULE_KEYS = (
    SYMBOLS,
    LBA_FILESYSTEM,
    VERSIONS,
    ENCODING_TABLES,
)

MODULE_FOLDERS = {
    SYMBOLS: "Symbols",
    LBA_FILESYSTEM: "LBA File System",
    VERSIONS: "Versions",
    ENCODING_TABLES: "Encoding Tables",
}

MODULE_SUFFIXES = {
    SYMBOLS: "symbols",
    LBA_FILESYSTEM: "lba",
}

VERSION_PATH_PREFIX = "version:"


def safe_stem(value: str) -> str:
    allowed = [char if char.isalnum() else "_" for char in Path(value).stem]
    return "_".join("".join(allowed).strip("_").split("_")) or "workspace"
