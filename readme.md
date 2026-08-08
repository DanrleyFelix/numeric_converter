![Python](https://img.shields.io/badge/Python-3.11-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.10.1-green)
![QtAwesome](https://img.shields.io/badge/QtAwesome-1.4.0-8A2BE2)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![Build](https://img.shields.io/badge/Build-PyInstaller-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

# Numeric WorkBench

Numeric WorkBench is a portable PySide6 desktop application for numeric
conversion, command expressions, workspace persistence and binary editing.

The project now contains two main workbenches:

- `Numeric WorkBench`: a live Decimal, Binary, Hex (BE) and Hex (LE) converter
  with an expression command window.
- `Binary Workbench`: a tabbed binary and assembly editing environment focused
  on PSX MIPS R3000A workflows, symbols, versions, mapped internal files and
  repeatable patch work.

The in-app Guide remains the user-facing manual. This README focuses on project
capabilities, technical structure and release/build notes.

## Highlights

- Converts between Decimal, Binary, Hex Big-Endian and Hex Little-Endian.
- Keeps typed converter content separate from formatted display output.
- Supports independent grouping and zero padding for each converter field.
- Evaluates arithmetic, comparison, bitwise and textual-operator expressions.
- Supports decimal, `0b` binary, `b'...'` binary, `0x` hexadecimal and plain
  hexadecimal command literals.
- Stores variables, command history, converter state and preferences in context.
- Provides separate Variables and Logs windows for inspecting workspace state.
- Lets Logs preferences decide which command categories are persisted.
- Includes Binary Workbench for files, scratch assembly, tabs, versions, symbols,
  labels, internal files, offset regions, decoded text and search/navigation.
- Builds portable bundles for Windows, Linux and macOS through PyInstaller.

## What's New in v3.1

v3.1 is a stabilization release focused on responsiveness, predictable editing
and direct navigation across large Binary Workbench projects.

- Binary Workbench now includes a PSX MIPS debugger with Run, Pause, Stop,
  Restart, Step, Step Over and Config actions, each exposed through the debugger
  toolbar and its corresponding `F5` through `F11` shortcut.
- Editor Assembly supports debugger directives such as
  `virtual_memory_range`, `import`, `define` and `ignore`. They configure the
  isolated runtime address space, load code and data, initialize registers and
  mark addresses that the debugger should ignore.
- The debugger window combines an instruction panel, editable hexadecimal and
  decimal registers, and a runtime panel with Stack View, Memory View,
  Breakpoints and Debug Log. Memory View can follow writes, reads or both.
- Debugger Config controls the automatic instruction interval in milliseconds
  and which Execution, Memory, Info, Warning and Error events appear in Debug
  Log. Log search, syntax highlighting and bounded high-volume rendering are
  included.
- Breakpoints can stop on execution, memory reads, memory writes or register
  conditions. Address types can be combined, while register breakpoints accept
  comparison and logical expressions and can be created from the register
  panel.
- Binary Workbench label folding received synchronization fixes for three or
  more labels and any combination of visible columns. Expanding the final label
  no longer truncates scrolling, deleting a label expands the label that
  receives its instructions, and edits inside collapsed content expand the
  affected label automatically.
- Editor consistency is now incremental and viewport-oriented. File Offset,
  Reference Offsets, Bytes, Raw Instructions and assembly projections are
  refreshed for the visible region first, avoiding unnecessary whole-document
  work during ordinary typing, scrolling, folding and navigation.
- Local and Global Symbols use indexed repositories and virtualized Model/View
  dialogs. Large symbol catalogs no longer create one permanent widget or one
  regular expression per entry, and inactive tabs are not materialized merely
  because a catalog was loaded.
- Numeric WorkBench Variables and Logs also use virtualized tables. Numeric and
  Binary autosave, completion and background state are isolated so activity in
  one workbench does not trigger processing in the other.
- Byte editing received fixes for insertion, deletion, multi-line replacement,
  undo/redo, cursor preservation and synchronization back to Editor Assembly.
  Protected directive, label and comment rows continue to follow the configured
  byte-shifting rules.
- The packaged Windows build includes the Unicorn native runtime required by
  the debugger.

### Faster navigation

Navigation no longer depends on a full assembly pass when the requested data is
already available. Users can move directly through labels, Local and Global
Symbol occurrences, Search, Go To, Offset Regions, LBA File System, hazards,
branches and jumps. Label navigation uses a lightweight per-tab index and
binary search; folding and scrolling request only the newly visible viewport.
Repeated navigation reuses cached data until the Assembly source changes.

This makes large files easier to explore: collapse a label to scan neighboring
blocks, open the Labels dialog to jump by name, inspect a Symbol's offsets, or
follow an address from Search without manually locating its line.

### Stability and performance fixes

- Fixed disappearing or stale offsets after inserting, deleting, pasting,
  undoing or editing invalid Assembly lines.
- Fixed synchronized scrolling with three or more labels, collapsed blocks and
  optional Reference Offset or Decoded Text columns.
- Fixed stale folding controls, truncated scroll ranges and content revealed by
  collapse/expand without an immediate viewport refresh.
- Fixed byte-column selection/copy regressions, destructive right-click
  selection changes and obsolete derived edits entering user undo history.
- Fixed branch, jump, label and Symbol refresh paths that previously performed
  repeated global work.
- Reduced startup and workspace recovery work by materializing active content
  on demand and offering safe recovery for unusually large sessions.
- Removed per-row widgets from scalable Environment, Variables and Logs views,
  preserving filtering, sorting, inline editing and multi-selection.
- Improved debugger memory, stack, register, breakpoint and log behavior,
  including stack address handling and packaged Unicorn loading.

## Numeric WorkBench

The numeric side combines a converter and a command window.

### Converter

The converter has four fields:

- `Decimal`: accepts digits `0-9`.
- `Binary`: accepts digits `0` and `1`.
- `Hex (BE)`: accepts digits `0-9` and letters `A-F`.
- `Hex (LE)`: accepts digits `0-9` and letters `A-F`.

Formatting is presentation-oriented. Grouping and zero padding change the
effective display/conversion value without overwriting the raw text being
edited. Odd hexadecimal input receives one leading zero before conversion so
byte alignment stays stable.

Normal copy keeps the displayed text, including spaces. The small copy icon
beside each converter field copies the same value without spaces.

### Command Window

The command window evaluates expressions and stores variables in the active
context.

Supported numeric literals:

```text
42
0b101010
b'101010
0x2A
002A
```

Assignments work with or without spaces:

```text
gp=0x89823A
mask = 0xFF
bits=b'10101010
```

Operators:

```text
Arithmetic:  +  -  *  /  %  **
Bitwise:     &  |  ^  ~  <<  >>
Comparison:  ==  !=  <  >  <=  >=
Aliases:     NOT  AND  OR  XOR
```

Textual aliases are parsed only when they are explicit operators. Identifiers
such as `AND_value`, `ORBIT`, `XOFFSET` and `NOT1` remain identifiers.

`ANS` stores the last successful command result. When `Convert` is enabled,
successful non-negative integer results are sent to the Decimal converter.

### Variables, Logs and Preferences

Variables and Logs open as separate reusable windows. Each row can be removed
individually. Logs are stored as submitted command/result pairs, and
`Preferences > Logs` controls whether assignment-only, unary-only, no-operator,
assignment and binary-operator expressions are persisted.

## Binary Workbench

Binary Workbench is a separate window opened from the main toolbar. It is built
around tabs, where each tab owns its file/source identity, rows, symbols,
versions, navigation state and dirty state.

### User-Facing Systems

- `Open File` opens binary or assembly/code files. Opening an already-open file
  switches to its existing tab.
- `New Scratch Code` creates a temporary assembly tab for experiments.
- `Internal Files` opens mapped ranges from a larger binary or disc image as
  focused tabs.
- `Version` stores named edit sets and can restore or replace visible edited
  rows without immediately rewriting the original file.
- `Go to`, `Find`, `Hazards`, `Select Block` and `Replace Bytes` provide focused
  navigation, delay-hazard review, range selection and byte replacement.
- `Environment` tools manage symbols, labels, offset regions, LBA file maps,
  custom commands and encoding tables.
- `Preferences` controls byte formatting, visible columns, edit rules,
  reference offsets, CPU architecture, block size, cache size and selection
  limits.

### Editor Model

The main editor view is made of synchronized row surfaces:

- `Editor Assembly`: the primary assembly editing surface.
- `Bytes`: encoded bytes for the same rows.
- `Raw Instructions`: preprocessed instruction text sent to assembly logic.
- `File Offset` and optional reference offsets.
- `Decoded Text`, when enabled through view preferences and encoding tables.

Rows are represented by `BinaryWorkbenchRowDTO`, which carries offsets,
instruction text, byte text and original values. The editor tracks meaningful
edits through overlays rather than blindly rewriting full source data. Bytes
editing preserves comments and supports Backspace/Delete without shifting rows
when byte shifting rules protect existing offsets.

The PSX MIPS R3000A codec lives under `src/core/binary_workbench/mips_r3000a`.
It uses project fallback assemblers/disassemblers and can use `capstone` and
`keystone` when available. This keeps the editor usable while still allowing
better assembly/disassembly support in packaged builds.

### Tabs and Context

Binary Workbench state is represented by `BinaryWorkbenchStateDTO` and
`BinaryWorkbenchTabContextDTO`.

The global state stores:

- open tabs;
- active tab id;
- shared view preference flag;
- last used directories;
- custom commands grouped by architecture;
- encoding tables;
- window size.

Each tab context stores:

- tab id, kind, display name and source path;
- CPU architecture and read mode;
- reference offsets and reference offset bases;
- labels, tab-local symbols, effective Local/Global Symbol values and symbol offsets;
- internal file mappings and parent/child tab metadata;
- LBA sector size and offset regions;
- versions and active version name;
- workspace/module paths, checksums and directories;
- custom commands, navigation history and last open offset;
- original rows, current rows, file sizes, overlays and dirty state;
- view preferences for visible columns and decoded text tables.

### Workspace Modules

Binary Workbench workspaces use a manifest plus module files instead of storing
everything in one large JSON payload.

The manifest is stored under:

```text
data/binary_workbench/workspaces
```

Module folders include:

```text
Symbols
LBA File System
Versions
Offset Regions
```

The manifest records source identity, module paths, module directories, active
version and view preferences. Module checksums are used to detect whether the
tab data has changed. Symbols, LBA maps, versions and offset regions can be
saved independently while still loading through the same tab workspace.

### Caching and Large Files

Binary Workbench uses two main caching systems.

`CachedBinaryReader` reads source files by block and keeps a limited LRU block
cache. `block_size` and `cache_max_blocks` are controlled by Advanced
Configuration. The reader can also apply byte overlays at read time, so edited
bytes are visible without forcing a full file rewrite.

`SearchCacheService` caches Find results by query and searched ranges. Entries
have a TTL, a maximum entry count and hit-count/last-use eviction. It can return
partial cached offsets, report missing ranges and validate offsets before reuse.
The cache is intentionally separated from heavy context persistence so search
speed does not bloat normal workspace load/save flows.

### Symbols, Labels and Navigation

Symbols keep assembly readable:

- Variables use the `_name` form and are suited for addresses or offsets.
- Equates use the `@name` form and are suited for immediate constants.
- Raw Instructions shows resolved values after symbolic replacement.

Labels are detected from assembly rows and refreshed across tab/version changes.
Jump and branch operands that target labels can be clicked for navigation. Go To
can resolve file offsets, reference offsets, LBA values, labels, equates,
variables and named internal files. Clicking jump or branch targets records a
volatile per-tab/version return history, and `Alt+G` returns to the previous
clicked source offset. Reference-offset jumps use an explicit `&` prefix, such
as `jal &0x801D9274`, so standard file-offset jumps stay unambiguous.

### Hazards, Rules and Editing Safety

`Search > Hazards` opens an independent range-based window for delay-hazard
review. It reuses Find-style Start Offset, End Offset and Length controls, keeps
results in a JSON hazard cache keyed by offset and lists each hazard beside the
corresponding instruction. Results remain navigable while the window stays open,
and `Alt+H` opens the Hazards window from the Search menu.

The MIPS editor marks delay hazards and invalid jump/branch targets only in
Editor Assembly. Raw Instructions keeps showing the resolved instruction stream
without warning backgrounds. Hazard detection includes branch/jump delay-slot
cases and load/use register hazards. Invalid jump and branch targets account for
alignment, file limits and selected reference-offset settings.

Rules separate fixed-row patching from byte-shifting edits. When byte shifting is
disabled, valid original rows remain present and destructive selection deletes
clear row content instead of removing protected offsets. Extra invalid rows can
still be removed, and scratch-code tabs must be saved before workspace-backed
symbols, versions or environment modules are created.

### Versions, Overlays and Internal Files

Versions are named edit sets. They can store instruction overlays, line-based
instructions, comments and row payloads. A version can be loaded into a tab,
updated from the current editor state and saved as a module without rewriting the
original source file. Scratch tabs become workspace-capable after their first
save links the tab to a real file path.

Internal file tabs are mapped through the configured LBA File System. They keep
their parent source visible and map changes back to parent binary offsets, which
avoids manual offset math when editing named files inside a larger image.

### Commands and Encoding Tables

Editor commands are typed in Editor Assembly with a leading slash. `/sp` creates
a stack save/restore block. `/li` supports immediate loading, using a single
instruction when the value fits and `lui`/`ori` expansion when required. `/where`
creates branch-only loop templates with labels on the same line as their
instructions and delay-slot `nop` rows. Custom commands can store repeated
instruction blocks with optional register substitution.

Encoding tables map byte values to text for decoded text workflows. Find can
search decoded text after the relevant table is available to the active context.

## Project Structure

```text
main.py             official desktop launcher
build               release build automation and PyInstaller config
src/core            domain rules, converter, validators and binary logic
src/modules         DTOs, constants, service contracts and use cases
src/controllers     bridges between UI/presentation and use cases
src/presentation    repositories, formatters and PySide6 UI components
src/main            application composition and runtime defaults
tests               automated tests
data                local contexts, workspaces and runtime data
```

Important Binary Workbench areas:

```text
src/core/binary_workbench
src/core/binary_workbench/mips_r3000a
src/core/binary_workbench/search_cache
src/core/binary_workbench/editor/commands
src/modules/binary_workbench_*.py
src/presentation/repository/binary_workbench_workspace
src/presentation/ui/components/binary_workbench
```

## Dependencies

Runtime dependencies:

```text
capstone==5.0.7
keystone-engine==0.9.2
packaging==25.0
PySide6==6.10.1
PySide6_Addons==6.10.1
PySide6_Essentials==6.10.1
QtAwesome==1.4.0
QtPy==2.4.3
shiboken6==6.10.1
```

Build dependency:

```text
pyinstaller==6.16.0
```

## Run

```bash
python main.py
```

The repository-root `main.py` file is the official app entrypoint.

## Build

Portable bundles are built natively per operating system.

```bash
make build OS=windows
make build OS=linux
make build OS=macos
```

If your shell does not expose the desired Python interpreter on `PATH`, override
it explicitly:

```bash
make build OS=windows PYTHON=/path/to/python
```

Build artifacts are emitted into:

```text
dist/windows
dist/linux
dist/macos
```

Artifact names follow this format:

```text
numeric-workbench-v3.1-<os>-<architecture>
```

v3.1 ships portable bundles only. Native installers are intentionally out of
scope for this release.

The PyInstaller config keeps the bundle smaller by excluding unused Qt stacks
such as QtQuick, QML, WebEngine, Multimedia, OpenGL, SVG, PDF and several unused
Qt Addons. Binary Workbench assembly support keeps the dynamic `capstone` and
`keystone` imports available in packaged builds.

## CI Release Builds

GitHub Actions builds portable artifacts natively on:

- Windows
- Linux
- macOS

Each release build job installs dependencies, runs tests, builds the portable
artifact and uploads it as a workflow artifact.

## Test

```bash
pytest
```

For focused validation after build changes:

```bash
pytest tests/release
```

## Feedback and Roadmap

User feedback is necessary for the next development cycles. Please report bugs,
unexpected editor behavior, confusing workflows and feature requests with enough
context to reproduce the issue. This is especially important for Binary
Workbench because real binary editing workflows expose edge cases that are hard
to predict from isolated tests.

The v3.1 stabilization cycle reinforces the need for continued refactoring and better
organization. The UI layer grew quickly and now contains responsibilities that
should move toward controllers, presenters or core services. QSS files also need
cleanup, several UI files are spread without their own focused subfolders, and
some shared constants are duplicated across nearby systems. Future maintenance
should reduce this coupling before adding large new features.
