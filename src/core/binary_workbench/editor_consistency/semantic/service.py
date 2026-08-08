from __future__ import annotations

import re

from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.classification import declared_label
from src.core.binary_workbench.editor_consistency.models import (
    ContributionSnapshot,
    DerivedCopyResult,
    DerivedCopySnapshot,
    SemanticResult,
    SemanticSnapshot,
)
from src.core.binary_workbench.mips_r3000a.source_line_rows import (
    build_source_line_rows,
    labels_from_source_rows,
)
from src.core.binary_workbench.mips_r3000a.codec import JUMP_NAVIGATION_BASE
from src.core.binary_workbench.mips_r3000a.comments import split_comment
from src.core.binary_workbench.mips_r3000a.hazard_validator import validate_mips_hazards
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


_REFERENCE_JUMP = re.compile(
    r"\b(?P<mnemonic>j|jal)\s+&(?P<target>[@_]?[A-Za-z_][A-Za-z0-9_]*|[-+]?(?:0x[0-9A-Fa-f]+|\d+))",
    re.IGNORECASE,
)
_STANDARD_JUMP = re.compile(
    r"\b(?:j|jal)\s+(?P<target>[-+]?(?:0x[0-9A-Fa-f]+|\d+))",
    re.IGNORECASE,
)


def calculate_semantic_result(
    snapshot: SemanticSnapshot,
    token: CancellationToken,
) -> SemanticResult | None:
    """Calculate one complete semantic revision without accessing Qt objects."""

    return _calculate_semantic_result(
        snapshot,
        token,
        include_hazards=True,
    )


def calculate_derived_copy_result(
    snapshot: DerivedCopySnapshot,
    token: CancellationToken,
) -> DerivedCopyResult | None:
    """Prepare only the copied lines plus labels needed by their branches."""

    if token.is_cancelled() or not snapshot.lines:
        return None
    first = max(0, min(snapshot.first_line, len(snapshot.lines) - 1))
    last = max(first, min(snapshot.last_line, len(snapshot.lines) - 1))
    labels = _copy_labels(snapshot.lines, snapshot.contributions, token)
    if labels is None:
        return None
    start_offset = _contribution_prefix(snapshot.contributions, first)
    selected_lines = list(snapshot.lines[first : last + 1])
    rows = build_source_line_rows(
        selected_lines,
        list(snapshot.offset_names),
        dict(snapshot.offset_bases),
        snapshot.codec,
        start_offset,
        labels,
        dict(snapshot.variables),
        dict(snapshot.equates),
        False,
        token.is_cancelled,
    )
    if rows is None or token.is_cancelled():
        return None
    selected_snapshot = SemanticSnapshot(
        snapshot.owner,
        snapshot.source_revision,
        snapshot.generation,
        "",
        snapshot.codec,
        tuple(selected_lines),
        snapshot.offset_names,
        snapshot.offset_bases,
        snapshot.variables,
        snapshot.equates,
        snapshot.jump_reference_offset,
    )
    rows = _finalize_jump_rows(
        selected_snapshot,
        rows,
        labels,
        token,
        token.is_cancelled,
    )
    if rows is None or token.is_cancelled():
        return None
    return DerivedCopyResult(
        snapshot.owner,
        snapshot.source_revision,
        snapshot.generation,
        first,
        tuple(rows),
    )


def _copy_labels(
    lines: tuple[str, ...],
    contributions: ContributionSnapshot,
    token: CancellationToken,
) -> dict[str, str] | None:
    """Index label addresses without assembling copied-out source lines."""

    labels: dict[str, str] = {}
    offset = 0
    line_index = 0
    for chunk in contributions.chunks:
        for size in chunk:
            if token.is_cancelled():
                return None
            if line_index < len(lines):
                name = declared_label(lines[line_index])
                if name:
                    labels[name] = f"0x{offset:08X}"
            offset += size
            line_index += 1
    while line_index < len(lines):
        if token.is_cancelled():
            return None
        name = declared_label(lines[line_index])
        if name:
            labels[name] = f"0x{offset:08X}"
        line_index += 1
    return labels


def _contribution_prefix(snapshot: ContributionSnapshot, line: int) -> int:
    """Return a copied range base from immutable contribution chunks."""

    remaining = max(0, min(line, snapshot.row_count))
    total = 0
    for chunk, chunk_sum in zip(snapshot.chunks, snapshot.chunk_sums):
        if remaining >= len(chunk):
            total += chunk_sum
            remaining -= len(chunk)
            continue
        total += sum(chunk[:remaining])
        break
    return total


def _calculate_semantic_result(
    snapshot: SemanticSnapshot,
    token: CancellationToken,
    *,
    include_hazards: bool,
) -> SemanticResult | None:
    """Calculate source-derived rows without artificial CPU throttling."""

    def cancelled() -> bool:
        """Stop obsolete work cooperatively at the existing parser checkpoints."""

        return token.is_cancelled()

    if cancelled():
        return None
    codec = snapshot.codec
    rows = build_source_line_rows(
        list(snapshot.lines),
        list(snapshot.offset_names),
        snapshot.offset_bases,
        codec,
        0,
        None,
        snapshot.variables,
        snapshot.equates,
        False,
        cancelled,
    )
    if token.is_cancelled() or rows is None:
        return None
    labels = labels_from_source_rows(rows, 0, codec.word_size)
    for _ in range(2):
        rows = _finalize_jump_rows(snapshot, rows, labels, token, cancelled)
        if rows is None:
            return None
        updated_labels = labels_from_source_rows(rows, 0, codec.word_size)
        if updated_labels == labels:
            break
        labels = updated_labels
        rows = build_source_line_rows(
            list(snapshot.lines),
            list(snapshot.offset_names),
            snapshot.offset_bases,
            codec,
            0,
            labels,
            snapshot.variables,
            snapshot.equates,
            False,
            cancelled,
        )
        if rows is None:
            return None
    hazards = (
        tuple(validate_mips_hazards([row.instruction for row in rows]))
        if include_hazards
        else ()
    )
    if token.is_cancelled():
        return None
    return SemanticResult(
        snapshot.owner,
        snapshot.source_revision,
        snapshot.generation,
        tuple(rows),
        labels,
        hazards,
    )


def _finalize_jump_rows(
    snapshot: SemanticSnapshot,
    rows: list[BinaryWorkbenchRowDTO],
    labels: dict[str, str],
    token: CancellationToken,
    cancelled=None,
) -> list[BinaryWorkbenchRowDTO] | None:
    """Resolve configured reference jumps and reject invalid standard targets."""

    symbols = {
        **{name.casefold(): value for name, value in labels.items()},
        **{f"_{name.lstrip('_')}".casefold(): value for name, value in snapshot.variables.items()},
        **{f"@{name.lstrip('@')}".casefold(): value for name, value in snapshot.equates.items()},
    }
    reference_name = snapshot.jump_reference_offset
    reference_base = _safe_int(snapshot.offset_bases.get(reference_name, "0"))
    output: list[BinaryWorkbenchRowDTO] = []
    for index, row in enumerate(rows):
        if (cancelled or token.is_cancelled)():
            return None
        line = snapshot.lines[index] if index < len(snapshot.lines) else row.instruction
        encoded = row
        if reference_name and reference_name in snapshot.offset_bases:
            normalized = _normalized_reference_jump(line, symbols, reference_base)
            if normalized != line:
                offset = _safe_int(row.offsets.get("File", "-"), invalid=None)
                if offset is not None:
                    replacement = build_source_line_rows(
                        [normalized],
                        list(snapshot.offset_names),
                        dict(snapshot.offset_bases),
                        snapshot.codec,
                        offset,
                        labels,
                        dict(snapshot.variables),
                        dict(snapshot.equates),
                        True,
                        token.is_cancelled,
                    )
                    if replacement and replacement[0].bytes_text:
                        encoded = BinaryWorkbenchRowDTO(
                            row.offsets,
                            row.instruction,
                            replacement[0].bytes_text,
                            row.original_instruction,
                            row.original_bytes_text,
                        )
        if _invalid_standard_jump(line):
            encoded = BinaryWorkbenchRowDTO(
                encoded.offsets,
                encoded.instruction,
                "",
                encoded.original_instruction,
                encoded.original_bytes_text,
            )
        output.append(encoded)
    return output


def _normalized_reference_jump(line: str, symbols: dict[str, str], base: int) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group("target")
        value = _safe_int(symbols.get(token.casefold(), token), invalid=None)
        target = None if value is None else value - base
        if target is None or target < 0 or target % ROW_BYTES:
            return match.group(0)
        return f"{match.group('mnemonic')} 0x{target + JUMP_NAVIGATION_BASE:08X}"

    return _REFERENCE_JUMP.sub(replace, line)


def _invalid_standard_jump(line: str) -> bool:
    code, _, _ = split_comment(line)
    match = _STANDARD_JUMP.search(code)
    if match is None:
        return False
    value = _safe_int(match.group("target"), invalid=None)
    return value is not None and (
        value < JUMP_NAVIGATION_BASE
        or (value - JUMP_NAVIGATION_BASE) % ROW_BYTES != 0
    )


def _safe_int(value: str, *, invalid: int | None = 0) -> int | None:
    try:
        return int(value, 0)
    except (TypeError, ValueError):
        return invalid
