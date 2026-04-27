# Numeric WorkBench

Numeric WorkBench is a desktop calculator for numeric conversion, command expressions, variables, context persistence and reusable command history.

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
- Copies converter text exactly as displayed, or copies raw text without spaces from the small copy icon beside each field.
- Evaluates arithmetic, comparison, bitwise and textual-operator expressions.
- Supports decimal, `0b` binary and `0x` hexadecimal literals.
- Supports assignments with Python-compatible variable names.
- Provides autocomplete for variables stored in the active context.
- Saves and loads workspace files containing the full context.
- Keeps an automatic default context file.
- Sends command results into the converter when the `Convert` toggle is enabled.
- Provides a key panel for fast command input.
- Includes an in-app Help window with focused usage documentation.

## Converter

The converter has four fields:

- `Decimal`: accepts digits `0-9`.
- `Binary`: accepts digits `0` and `1`.
- `Hex (BE)`: accepts digits `0-9` and letters `A-F`.
- `Hex (LE)`: accepts digits `0-9` and letters `A-F`.

### Editing and copying

Converter fields behave like normal text fields for selection, cursor movement and standard copy:

- `Ctrl+C` copies the selected value exactly as it appears on screen, including spaces.
- `Ctrl+A` selects the visible field content.
- `Backspace` and `Delete` remove the selected raw content or the raw character near the cursor.
- The small copy icon beside each field performs `copy raw`, which copies the visible value without spaces.

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
ANS + 4
```

`ANS` always contains the last successful command result and can be reused like a normal variable.

Bitwise:

```text
mask=0xFF
mask AND 0b10101010
NOT 0x0F
(0x20 + 5) << 2
```

Command results appear in the result label above the input. When `Convert` is enabled, successful non-negative integer results are also sent to the Decimal converter field.

History entries are rendered on one line:

```text
x=5665+58*(40-23) => 6651
```

## Workspace and Context

Context stores the working state:

- variables;
- command history;
- active command line;
- converter state;
- key panel visibility.

Workspace files save the full context:

```text
data/workspaces
```

Use:

- `File > Save Workspace`
- `File > Load Workspace`

The automatic default context is stored internally in:

```text
data/contexts
```

The default context is saved automatically as the workspace changes.

## Key Panel

The key panel writes directly into the command window.

Special keys:

- `CLEAR`: deletes the last command character, or removes one line from History when the command input is empty.
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
- context and history;
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
data              local contexts and workspaces
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

# Corrigindo bugs

## Em relação ao Key Panel (apenas ajuste moderado):
Ao clicar nas teclas NOT, OR, AND e XOR insere-se automaticamente um " " (espaço), uma vez que, por exemplo, NOT1 seria uma varíavel. Então ao clicar em NOT ficará "NOT " (o mesmo para os outros operadores que possuem teclas válidas para variáveis).

## Bugs críticos
É IMPOSSÍVEL criar varíaveis que começam com AN, O E XO. Isso se deve ao fato de existirem operadores não unários que usam letras normais como AND, OR E XOR. Isso significa que esses operadores e o NOT, de forma particular e excepcional, devem ser interpretados como operadores apenas se houver espaço ou parênteses entre os operandos. Exemplo 1: A AND B (AND É OPERADOR). AANDB (AND não é operador). (A)AND(B) (AND é operador). 
Exemplo 2: NOT1 (NOT não é operador). NOT 1 (NOT é operador). NOT(1) (NOT é operador).
Exemplo 3: (NOT)1, A(OR)B são EXPRESSÕES INVÁLIDAS. OPERADORES NÃO PODEM FICAR ENTRE PARÊNTESES.
Obs: Tome cuidado ao corrigir este bug, pois você pode quebrar outras funcionalidades. Um exemplo de erro que você pode cometer é proibir que a seguinte expressão não possa ser digitada: (A AND B)OR(B XOR 1). Caso A seja uma variável desconhecida, a interface deve colocar na zona de output "Unknown variable "A"". Essa expressão É VÁLIDA.

# Ajustes na interface (UI/UX)
## Em relação a toolbar:
File: Save Workspace possui um espaçamento que não deveria em existir no "top". Load Workspace possui um espaçamento que não deveria em existir no "bottom".
Preferences: Acontece a mesma coisa que no File. O Show Key Panel aparece de forma redundante no converter. Outro erro consiste em colocar borda quando show key panel está ativado. Ao invés disso, use um ícone verde de "verified" quando ativo.
## Em relação ao output do command window:
O texto "Type an Expression and Press Enter" deve ser azul e não amarelo. 
Ao digitar, por exemplo, "NOT1", aparece CORRETAMENTE "Expression Incomplete" em AMARELO, mao pressionar ENTER, aparece "Invalid Expression" em AMARELO. Para expressões incorretas, sempre deve-se usar o vermelho após pressionar a tecla ENTER.

## Em relação ao Help
O título na janela de Help deve ser apenas User Guide ao invés de Help. E "Numeric WorkBench user guide" não deve existir. 
Adicione um padding em relação ao conteúdo/títulos/subtítulos etc. em relação ao preenchimento no fundo. O texto está muito colado com o fundo do panel.
Essa cor de fundo só deve existir nos títulos e subtítulos. Use outra tonalidade da cor para textos com size normal (que não seja título e nem subtítulo).

