from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, Flag, auto
from collections.abc import Mapping

from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.modules.contracts import CPUArchCodec
from src.core.binary_workbench.mips_r3000a.hazard_validator import MipsHazard


class ChangeKind(str, Enum):
    """Classify one aggregated source edit by its derived impact."""

    LOCAL = "local"
    LOCAL_DEPENDENCY = "local_dependency"
    STRUCTURAL = "structural"


class ConsistencyState(Flag):
    """Expose independent visual, semantic, and immediate phases."""

    CLEAN = 0
    DIRTY_VISUAL = auto()
    RECALCULATING_VISUAL = auto()
    DIRTY_SEMANTIC = auto()
    RECALCULATING_SEMANTIC = auto()
    RECALCULATING_IMMEDIATE = auto()


class DerivedCategory(Flag):
    """Name independently pending viewport projections."""

    NONE = 0
    OFFSETS = auto()
    ASSEMBLY = auto()
    BYTES = auto()
    RAW = auto()
    SYMBOLS = auto()
    LABELS = auto()
    BRANCHES = auto()
    HAZARDS = auto()
    HIGHLIGHT = auto()


@dataclass(frozen=True)
class EditorOwner:
    """Identify the tab/version activation that owns derived results."""

    tab_id: str
    version_id: str
    activation_epoch: int


@dataclass(frozen=True)
class DirtyRange:
    """Represent one inclusive range of dirty source lines."""

    first: int
    last: int


@dataclass(frozen=True)
class ContributionSnapshot:
    """Share immutable emitted-size segments with an offset worker."""

    chunks: tuple[tuple[int, ...], ...]
    chunk_sums: tuple[int, ...]
    row_count: int


@dataclass(frozen=True)
class OffsetDistributionBatch:
    """Carry only File and Reference Offset projection values."""

    owner: EditorOwner
    structural_revision: int
    generation: int
    first: int
    last: int
    values: tuple[tuple[int, dict[str, str]], ...]


@dataclass(frozen=True)
class LineContentBatch:
    """Carry source-revision-bound derived content for selected lines."""

    owner: EditorOwner
    source_revision: int
    generation: int
    rows: tuple[tuple[int, BinaryWorkbenchRowDTO], ...]


@dataclass(frozen=True)
class SemanticSnapshot:
    """Hold the immutable source and configuration for semantic work."""

    owner: EditorOwner
    source_revision: int
    generation: int
    architecture: str
    codec: CPUArchCodec
    lines: tuple[str, ...]
    offset_names: tuple[str, ...]
    offset_bases: Mapping[str, str]
    variables: Mapping[str, str]
    equates: Mapping[str, str]
    jump_reference_offset: str = ""


@dataclass(frozen=True)
class SemanticResult:
    """Return one atomically applicable global semantic snapshot."""

    owner: EditorOwner
    source_revision: int
    generation: int
    rows: tuple[BinaryWorkbenchRowDTO, ...]
    labels: dict[str, str]
    hazards: tuple[MipsHazard, ...] = ()


@dataclass(frozen=True)
class ConsistentEditorSnapshot:
    """Expose a complete revision for persistence or debugging."""

    owner: EditorOwner
    source_revision: int
    structural_revision: int
    rows: tuple[BinaryWorkbenchRowDTO, ...]
    labels: dict[str, str]


@dataclass(frozen=True)
class ConsistencyBarrierResult:
    """Describe success or failure of one synchronous consistency barrier."""

    success: bool
    snapshot: ConsistentEditorSnapshot | None = None
    error: str | None = None
