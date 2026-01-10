from typing import Protocol, Optional
from src.application.dto.conversion_result import ConversionResultDTO


class IConverterUseCase(Protocol):

    def execute(self, from_type: str, value: str) -> dict[str, object]:
        pass


class IConverterController(Protocol):
    
    def on_input_changed(self, from_type: str, raw_value: str) -> Optional[ConversionResultDTO]:
        pass


class IConverterPresenter(Protocol):

    def on_user_input(self, from_type: str, raw_value: str) -> Optional[dict[str, str]]:
        pass