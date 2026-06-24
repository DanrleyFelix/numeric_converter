from dataclasses import dataclass, field

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE


@dataclass(frozen=True)
class BinaryWorkbenchInternalFileDTO:
    name: str
    start_lba: int


@dataclass(frozen=True)
class BinaryWorkbenchEncodingTableDTO:
    name: str
    values: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BinaryWorkbenchOffsetRegionDTO:
    name: str
    offset: int
    details: str = ""


@dataclass(frozen=True)
class BinaryWorkbenchLbaFilesystemDTO:
    name: str
    file_identifiers: list[str] = field(default_factory=list)
    sector_size: int = BINARY_WORKBENCH_DEFAULT_LBA_SECTOR_SIZE
    internal_files: list[BinaryWorkbenchInternalFileDTO] = field(default_factory=list)


@dataclass(frozen=True)
class BinaryWorkbenchSymbolsDTO:
    name: str
    file_identifiers: list[str] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    equates: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
