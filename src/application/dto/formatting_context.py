from dataclasses import dataclass


@dataclass(frozen=True)
class FormattingOutputDTO:
    group_size: int = 0
    zero_pad: bool = False
