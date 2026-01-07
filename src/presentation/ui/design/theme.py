from dataclasses import dataclass


@dataclass(frozen=True)
class ColorPalette:
    BACKGROUND = "#0E1117"
    SURFACE = "#161B22"
    BORDER = "#30363D"

    TEXT_PRIMARY = "#E6EDF3"
    TEXT_SECONDARY = "#9BA3AF"

    DECIMAL = "#7DD3FC"
    DECIMAL_ZERO = "#BAE6FD"

    BINARY = "#A7F3D0"
    BINARY_ZERO = "#D1FAE5"

    HEX = "#FCA5A5"
    HEX_ZERO = "#FECACA"

    VARIABLE = "#C7D2FE"
    OPERATOR = "#FBBF24"
    PAREN = "#94A3B8"


PALETTE = ColorPalette()
