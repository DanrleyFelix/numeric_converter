"""Compatibility imports for the split per-tab Symbol runtime."""

from src.core.binary_workbench.symbols.tab_runtime import (
    MaterializedSymbolTab,
    SymbolRuntime,
    matching_source_lines as _matching_source_lines,
)

__all__ = ["MaterializedSymbolTab", "SymbolRuntime", "_matching_source_lines"]
