from src.modules.constants import HEX_KEYS


class KEY_PANEL_SIZE:
    BUTTON_MIN_HEIGHT: int = 34
    BUTTON_MIN_WIDTH: int = 56


class KEY_PANEL_LAYOUT:
    MARGIN: int = 12
    H_SPACING: int = 12
    V_SPACING: int = 12


KEY_PANEL_KEYS: list[str] = [
    *HEX_KEYS,
    "+", "-", "x", "/", "^", "==", "!=", ">=", "<=",
    "=", "&", "|", "~", "NOT", "OR", "AND", "XOR", ">>", "<<",
    "(", ")", "0x", "0b",
    "CLEAR", "ENTER",
]
