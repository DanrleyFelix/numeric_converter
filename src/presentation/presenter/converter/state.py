from __future__ import annotations

from dataclasses import dataclass, field

from src.presentation.presenter.converter.constants import CONVERTER_TYPE
from src.presentation.presenter.converter.field_maps import empty_converter_text_map


@dataclass
class ConverterState:
    current_value: str = ""
    current_from_type: str = CONVERTER_TYPE.DECIMAL
    raw_inputs: dict[str, str] = field(default_factory=empty_converter_text_map)
    last_output: dict[str, str] = field(default_factory=empty_converter_text_map)
    last_error_message: str | None = None

    def reset_outputs(self) -> dict[str, str]:
        self.current_value = ""
        self.last_error_message = None
        self.raw_inputs = empty_converter_text_map()
        self.last_output = empty_converter_text_map()
        return dict(self.last_output)
