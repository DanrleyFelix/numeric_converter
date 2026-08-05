from src.core.binary_workbench.symbols.compatibility.legacy import (
    AdaptedSymbols,
    LegacySymbolMutationAdapter,
    LegacySymbolOffsetsAdapter,
    LegacySymbolsMappingView,
    LegacySymbolsPayloadAdapter,
    definitions_payload,
)
from src.core.binary_workbench.symbols.compatibility.migration import (
    LazyTabDescriptor,
    SYMBOL_SCHEMA_VERSION,
    SymbolMigrationReport,
    SymbolSchemaMigrator,
)

__all__ = [
    "AdaptedSymbols",
    "LazyTabDescriptor",
    "LegacySymbolMutationAdapter",
    "LegacySymbolOffsetsAdapter",
    "LegacySymbolsMappingView",
    "LegacySymbolsPayloadAdapter",
    "SYMBOL_SCHEMA_VERSION",
    "SymbolMigrationReport",
    "SymbolSchemaMigrator",
    "definitions_payload",
]
