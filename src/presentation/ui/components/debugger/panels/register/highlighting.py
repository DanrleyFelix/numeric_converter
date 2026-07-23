"""Debugger register-table colors based on Binary Workbench highlighters."""

from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_highlight_color,
    psx_mips_required_highlight_color,
)


def register_cell_color(column: int, value: str) -> str | None:
    """Return the existing Binary Workbench color for one register cell."""

    if column == 0:
        register = "$sp" if value == "pc" else value
        return psx_mips_highlight_color("registers", register)
    if column in {1, 2}:
        return psx_mips_required_highlight_color("hex")
    return None
