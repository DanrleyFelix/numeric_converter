from src.core.converter import Converter


class ConverterUseCase:
    def execute(self, from_type: str, value: str) -> dict[str, object]:
        return Converter.convert(from_type, value)
