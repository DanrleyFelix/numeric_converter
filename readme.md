# Numeric WorkBench

Numeric WorkBench is a desktop calculator for numeric conversion, command expressions, variables, context persistence and execution logs.

It combines two main tools:

- a live converter for Decimal, Binary, Hex (BE) and Hex (LE);
- a command window for expressions, assignments, operators and reusable variables.

## Features

- Converts between Decimal, Binary, Hex Big-Endian and Hex Little-Endian.
- Restricts each converter input to the characters accepted by its numeric base.
- Keeps typed converter content separate from formatted display output.
- Applies `group size` and `zero padding` independently for each converter field.
- Completes odd hexadecimal input with a leading zero before conversion.
- Keeps Hex (LE) editing stable even when zero padding is visible.
- Evaluates arithmetic, comparison, bitwise and textual-operator expressions.
- Supports decimal, `0b` binary and `0x` hexadecimal literals.
- Supports assignments with Python-compatible variable names.
- Provides autocomplete for variables stored in the active context.
- Saves and loads workspace files containing context and log together.
- Keeps automatic default context and log files.
- Sends command results into the converter when the `Convert` toggle is enabled.
- Provides a key panel for fast command input.
- Includes an in-app Help window with focused usage documentation.

## Converter

The converter has four fields:

- `Decimal`: accepts digits `0-9`.
- `Binary`: accepts digits `0` and `1`.
- `Hex (BE)`: accepts digits `0-9` and letters `A-F`.
- `Hex (LE)`: accepts digits `0-9` and letters `A-F`.

### Padding and grouping

Each field can be configured in `Preferences > Converter`:

- `group size` defines how characters are grouped visually.
- `zero pad` pads the effective value before display and conversion.

The raw typed content is not overwritten by padding. For example, with Hex (LE), `group size = 4` and `zero pad = true`:

```text
typed: 45
effective/displayed: 0045

typed: 454
effective/displayed: 0454
```

Odd hexadecimal input is completed with one leading zero before conversion:

```text
typed: FFF0123
effective: 0FFF0123
```

## Command Window

The command window evaluates expressions and stores variables in the active context.

### Numbers

```text
42
0b101010
0x2A
```

### Assignments

Assignments work with or without spaces:

```text
gp=0x89823A
mask = 0xFF
bits=0b10101010
```

Variable names follow Python identifier rules.

### Operators

Arithmetic:

```text
+  -  *  /  %  **
```

Bitwise:

```text
&  |  ^  ~  <<  >>
```

Comparisons:

```text
==  !=  <  >  <=  >=
```

Textual aliases:

```text
NOT  AND  OR  XOR
```

### Examples

Basic:

```text
1 + 1
0x10 + 5
0b1010 * 3
```

Variables:

```text
value=0x20
value + 10
value << 2
```

Bitwise:

```text
mask=0xFF
mask AND 0b10101010
NOT 0x0F
(0x20 + 5) << 2
```

Command results appear in the result label above the input. When `Convert` is enabled, successful non-negative integer results are also sent to the Decimal converter field.

## Workspace, Context and Logs

Context stores the working state:

- variables;
- command history;
- active command line;
- converter state;
- key panel visibility.

Logs store executed command lines and their results:

```text
expression -> result
```

Workspace files save context and log together:

data/workspaces
```

Use:

- `File > Save Workspace`
- `File > Load Workspace`

The automatic defaults are still stored internally in:

```text
data/contexts
data/logs
```

The default context and default log are saved automatically as the workspace changes.

## Key Panel

The key panel writes directly into the command window.

Special keys:

- `LOG`: toggles between History and Log.
- `CLEAR`: deletes the last command character, or removes one line from the active History/Log panel when the command input is empty.
- `ENTER`: submits the current expression.

## Preferences

`Preferences > Converter` controls formatting for each converter field:

- group size;
- zero padding.

`Preferences > Show Key Panel` toggles the key panel.

Checked preference items are highlighted with the project theme instead of a default check icon.

## Help

The `Help` toolbar button opens an in-app manual with pages for:

- overview;
- converter;
- command window;
- context and logs;
- key panel;
- preferences.

## Project Structure

```text
src/core          domain rules, converter, tokenizer, validator and context
src/application   contracts, DTOs, services and use cases
src/controllers   bridges between presenters and use cases
src/presentation  presenters, repositories, formatters and UI components
src/main          application composition
tests             automated tests
data              local contexts and logs
```

## Dependencies

```text
packaging==25.0
PySide6==6.10.1
PySide6_Addons==6.10.1
PySide6_Essentials==6.10.1
QtAwesome==1.4.0
QtPy==2.4.3
shiboken6==6.10.1
pytest
```

## Run

```bash
python -m src
```

## Test

```bash
pytest
```
