from __future__ import annotations

from dataclasses import dataclass

from src.core.binary_workbench.editor_consistency.models import ChangeKind, DirtyRange
from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.binary_workbench.mips_r3000a.source_line_rows import split_label


@dataclass(frozen=True)
class LineChange:
    """Describe the byte and symbol impact of one source line change."""

    kind: ChangeKind
    previous_size: int
    current_size: int


def classify_line_change(
    previous_size: int,
    current_size: int,
    *,
    line_count_changed: bool = False,
    label_changed: bool = False,
) -> LineChange:
    """Classify a line using emitted size rather than keyboard activity."""

    structural = line_count_changed or previous_size != current_size
    if structural:
        kind = ChangeKind.STRUCTURAL
    elif label_changed:
        kind = ChangeKind.LOCAL_DEPENDENCY
    else:
        kind = ChangeKind.LOCAL
    return LineChange(kind, max(0, previous_size), max(0, current_size))


def merge_dirty_ranges(
    ranges: tuple[DirtyRange, ...] | list[DirtyRange],
    added: DirtyRange,
) -> tuple[DirtyRange, ...]:
    """Merge touching dirty ranges into a compact sorted tuple."""

    pending = sorted((*ranges, added), key=lambda item: (item.first, item.last))
    merged: list[DirtyRange] = []
    for item in pending:
        normalized = DirtyRange(max(0, item.first), max(item.first, item.last))
        if not merged or normalized.first > merged[-1].last + 1:
            merged.append(normalized)
            continue
        previous = merged[-1]
        merged[-1] = DirtyRange(previous.first, max(previous.last, normalized.last))
    return tuple(merged)


def declared_label(text: str) -> str:
    """Return the normalized label declared by one source line."""

    label, _ = split_label(strip_comment(text).strip())
    return label
