# Symbol stress source (v3)

This fixture contains a synthetic Assembly version with 1,500 Local Symbols and
10,000 Global Symbols. Load the two JSON libraries in their corresponding
Environment dialogs, then open `symbol_stress_11500_lines.asm`.

- `_local_symbol_NNNN` references the Local Symbols library.
- `@global_symbol_NNNNN` references the Global Symbols library.
- The source contains every Symbol at least once, plus labels, comments and the
  debugger directives required at the top of an Assembly file.

Run `python examples/symbol_stress_v3/generate.py` from the repository root to
recreate all generated files deterministically.
