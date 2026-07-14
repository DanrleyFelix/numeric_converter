from __future__ import annotations


def merged_symbol_values(
    symbols: dict[str, str] | None = None,
    variables: dict[str, str] | None = None,
    equates: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return one canonical symbol map from current and legacy fields."""

    merged: dict[str, str] = {}
    names_by_key: dict[str, str] = {}
    for values in (variables or {}, equates or {}, symbols or {}):
        for name, value in values.items():
            normalized = str(name).strip().lstrip("_@")
            if normalized:
                key = normalized.casefold()
                previous = names_by_key.get(key)
                if previous is not None and previous != normalized:
                    merged.pop(previous, None)
                merged[normalized] = str(value)
                names_by_key[key] = normalized
    return merged


def effective_symbol_values(
    local_symbols: dict[str, str],
    global_symbols: dict[str, str],
) -> dict[str, str]:
    """Merge session-global symbols with tab-local symbols."""

    return merged_symbol_values(
        merged_symbol_values(local_symbols),
        merged_symbol_values(global_symbols),
    )
