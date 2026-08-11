"""Debugger directive names and validation messages."""

DIRECTIVE_PREFIX = "*"
VIRTUAL_MEMORY_RANGE = "virtual_memory_range"
IMPORT = "import"
DEFINE = "define"
IGNORE = "ignore"

DEBUGGER_DIRECTIVE_NAMES = (
    VIRTUAL_MEMORY_RANGE,
    IMPORT,
    DEFINE,
    IGNORE,
)

ARGUMENT_COUNTS = {
    VIRTUAL_MEMORY_RANGE: 2,
    IMPORT: 2,
    DEFINE: 2,
    IGNORE: 2,
}

CURRENT_FILE = "current_file"

PSX_SCRATCH_HEADER = (
    "* virtual_memory_range 0x80000000 0x801DFFFF",
    "* import current_file 0x8000F800",
    "* define $sp 0x801FFF00",
    "* define $pc 0x8000F800",
    "* define $gp 0x8009AF08",
)
