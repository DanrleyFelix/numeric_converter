from __future__ import annotations

from typing import Any

from src.presentation.presenter.converter.constants import (
    CONVERTER_FIELD_KEYS,
    CONVERTER_TYPE,
)


def empty_converter_text_map() -> dict[str, str]:
    return {key: "" for key in CONVERTER_FIELD_KEYS.ALL}


def normalize_source_input(from_type: str, value: str) -> str:
    if from_type in (CONVERTER_TYPE.HEX_BE, CONVERTER_TYPE.HEX_LE):
        return value.upper()
    return value


def build_raw_outputs(
    from_type: str,
    cleaned: str,
    values: dict[str, Any],
) -> dict[str, str]:
    return {
        CONVERTER_TYPE.DECIMAL: (
            cleaned
            if from_type == CONVERTER_TYPE.DECIMAL
            else str(values[CONVERTER_TYPE.DECIMAL])
        ),
        CONVERTER_TYPE.BINARY: (
            cleaned
            if from_type == CONVERTER_TYPE.BINARY
            else str(values[CONVERTER_TYPE.BINARY])
        ),
        CONVERTER_TYPE.HEX_BE: (
            cleaned.upper()
            if from_type == CONVERTER_TYPE.HEX_BE
            else values[CONVERTER_TYPE.HEX_BE].hex().upper()
        ),
        CONVERTER_TYPE.HEX_LE: (
            cleaned.upper()
            if from_type == CONVERTER_TYPE.HEX_LE
            else values[CONVERTER_TYPE.HEX_LE].hex().upper()
        ),
    }
