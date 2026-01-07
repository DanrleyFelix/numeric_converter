from typing import Protocol
from src.application.dto.formatting_context import FormattingOutputDTO


class IOutputFormatter(Protocol):

    def format_decimal(self, value: int, formatter: FormattingOutputDTO) -> str:
        pass

    def format_binary(self, value: str, formatter: FormattingOutputDTO) -> str:
        pass

    def format_hex(self, value: bytes, formatter: FormattingOutputDTO) -> str:
        pass


class IFormattingPreferencesRepository(Protocol):

    def load(self) -> dict[str, FormattingOutputDTO]:
        pass

    def save(self, context: dict[str, FormattingOutputDTO]) -> None:
        pass


class IFormattingPreferencesService(Protocol):

    def get_format(self) -> dict[str, FormattingOutputDTO]:
        pass

    def update(self, key: str, ctx: FormattingOutputDTO):
        pass
