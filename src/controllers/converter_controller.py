from src.application.dto import ConversionResultDTO, FormattingOutputDTO
from src.application.contracts.converter_contract import IConverterUseCase


class ConverterController:

    def __init__(
        self,
        use_case: IConverterUseCase,
        formatting: dict[str, FormattingOutputDTO]):
        
        self._use_case = use_case
        self._formatting = formatting

    def convert(self, from_type: str, value: str) -> ConversionResultDTO:
        values = self._use_case.execute(from_type, value)
        return ConversionResultDTO(
            values=values,
            formatting=self._formatting,
            from_type=from_type)
