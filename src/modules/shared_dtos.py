from dataclasses import dataclass


@dataclass(frozen=True)
class WindowSizeDTO:
    width: int
    height: int
