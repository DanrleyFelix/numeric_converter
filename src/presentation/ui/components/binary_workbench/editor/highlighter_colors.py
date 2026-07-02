from src.presentation.ui.components.binary_workbench.editor.constants.highlighter_rules import (
    PSX_MIPS_HIGHLIGHTER,
)


def psx_mips_highlight_color(category: str, token: str = "") -> str | None:
    value = PSX_MIPS_HIGHLIGHTER.get(category)
    if isinstance(value, str):
        return value
    raw_token = token.strip()
    token_name = raw_token.lstrip("$").lower()
    if category == "registers" and token_name.isdecimal() and not raw_token.startswith("$"):
        return None
    if isinstance(value, list):
        for group, color in value:
            if token_name in group:
                return color
    return None


def psx_mips_required_highlight_color(category: str) -> str:
    color = psx_mips_highlight_color(category)
    if color is None:
        raise KeyError(category)
    return color
