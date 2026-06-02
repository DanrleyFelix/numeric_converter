from __future__ import annotations

from src.core.binary_workbench.mips_r3000a import PsxMipsR3000ACodec
from src.core.binary_workbench.mips_r3000a.preprocessor import (
    preprocess_instruction,
    strip_comment,
)
from src.core.binary_workbench.mips_r3000a.pseudo_instructions import (
    expand_pseudo_instruction,
)
from src.modules.dtos import BinaryWorkbenchRowDTO

ROW_BYTES = 4
DEFAULT_OFFSET = "0x00000000"


def without_blank_instruction_overlays(
    byte_overlays: dict[str, str],
    instruction_overlays: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    blank_offsets = {
        offset
        for offset, instruction in instruction_overlays.items()
        if not instruction.strip()
    }
    return (
        {offset: value for offset, value in byte_overlays.items() if offset not in blank_offsets},
        {offset: instruction for offset, instruction in instruction_overlays.items() if offset not in blank_offsets},
    )


def labels_from_instruction_overlays(overlays: dict[str, str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for offset, instruction in overlays.items():
        if label := label_from_instruction(instruction):
            labels[label] = offset
    return labels


def byte_overlays_from_instruction_overlays(
    overlays: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> dict[str, str]:
    codec = PsxMipsR3000ACodec()
    labels = labels_from_instruction_overlays(overlays)
    byte_overlays: dict[str, str] = {}
    for offset_text, instruction in sorted(overlays.items()):
        if not instruction.strip():
            continue
        offset = int(offset_text, 16)
        for index, expanded in enumerate(expand_pseudo_instruction(instruction)):
            target_offset = offset + (index * ROW_BYTES)
            address = target_offset
            assembly = preprocess_instruction(
                expanded,
                address,
                labels,
                variables,
                equates,
            )
            data = codec.assemble(assembly, address)
            if data is not None:
                byte_overlays[f"0x{target_offset:08X}"] = codec.bytes_text(data)
    return byte_overlays


def version_rows_from_instruction_overlays(
    overlays: dict[str, str],
    byte_overlays: dict[str, str],
    offset_names: list[str],
    offset_bases: dict[str, str],
) -> list[BinaryWorkbenchRowDTO]:
    rows: list[BinaryWorkbenchRowDTO] = []
    for offset_text, instruction in sorted(overlays.items()):
        offset = int(offset_text, 16)
        rows.append(
            BinaryWorkbenchRowDTO(
                offsets=offset_values(offset, offset_names, offset_bases),
                instruction=instruction,
                bytes_text=byte_overlays.get(offset_text, "00 00 00 00"),
            )
        )
    return rows


def instruction_overlays_from_rows(
    rows: list[BinaryWorkbenchRowDTO],
) -> dict[str, str]:
    return {
        row.offsets.get("File", DEFAULT_OFFSET): row.instruction
        for row in rows
        if row.instruction and row.offsets.get("File") != "-"
    }


def label_from_instruction(instruction: str) -> str:
    before_comment = strip_comment(instruction).strip()
    if ":" not in before_comment:
        return ""
    candidate = before_comment.split(":", 1)[0].strip()
    return candidate if candidate and " " not in candidate and "\t" not in candidate else ""


def offset_values(
    offset: int,
    offset_names: list[str],
    offset_bases: dict[str, str],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in offset_names:
        base = 0 if name == "File" else int(offset_bases.get(name, "0x0"), 0)
        values[name] = f"0x{base + offset:08X}"
    return values
