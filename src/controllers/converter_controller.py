from typing import Optional

from src.presentation.formatters.input_converter import InputFormatter
from src.core.converter import NumericValidator
from src.application.dto import FormattingOutputDTO, ConversionResultDTO
from src.application.contracts.converter_contract import IConverterUseCase


class ConverterController:
    
    def __init__(self, use_case: IConverterUseCase, formatting: dict[str, FormattingOutputDTO]):
        self.use_case = use_case
        self.formatting = formatting

    def on_input_changed(self, from_type: str, raw_value: str) -> Optional[ConversionResultDTO]:

        value = InputFormatter.format(raw_value)
        if not value:
            return None
        if not NumericValidator.validate(from_type, value):
            return None
        converted = self.use_case.execute(from_type, value)
        return {
            "values": converted,
            "formatter": self.formatting,
            "from_type": from_type}
