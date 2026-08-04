from __future__ import annotations

import re

from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.models import SemanticResult, SemanticSnapshot
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

    for index in range(0, len(snapshot.lines), 128):
        if token.is_cancelled():
            return None
    codec = snapshot.codec
    rows = build_source_line_rows(
        list(snapshot.lines),
        list(snapshot.offset_names),
        dict(snapshot.offset_bases),
        codec,
        0,
        None,
        dict(snapshot.variables),
        dict(snapshot.equates),
        False,
        token.is_cancelled,
    )
    if token.is_cancelled() or rows is None:
        return None
    labels = labels_from_source_rows(rows, 0, codec.word_size)
    for _ in range(2):
        rows = _finalize_jump_rows(snapshot, rows, labels, token)
        if rows is None:
            return None
        updated_labels = labels_from_source_rows(rows, 0, codec.word_size)
        if updated_labels == labels:
            break
        labels = updated_labels
        rows = build_source_line_rows(
            list(snapshot.lines),
            list(snapshot.offset_names),
            dict(snapshot.offset_bases),
            codec,
            0,
            labels,
            dict(snapshot.variables),
            dict(snapshot.equates),
            False,
            token.is_cancelled,
        )
        if rows is None:
            return None
    hazards = tuple(validate_mips_hazards([row.instruction for row in rows]))
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
        if token.is_cancelled():
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
