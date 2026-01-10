from dataclasses import dataclass
from src.modules.utils import COLOR


@dataclass(frozen=True)
class CommandRenderResultDTO:
    lines: list[str]
    color: COLOR