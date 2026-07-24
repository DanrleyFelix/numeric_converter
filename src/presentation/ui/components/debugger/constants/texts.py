"""User-facing debugger labels shared by actions and panels."""

DEBUGGER_TITLE = "Debugger"
DEBUGGER_START_REQUIRED = "Start a debugger session with F5 first."
DEBUGGER_WORKER_STOP_ERROR = "Unable to stop the debugger worker safely."
DEBUGGER_ACTIONS = (
    ("run", "Run", "F5"),
    ("pause", "Pause", "F6"),
    ("stop", "Stop", "F7"),
    ("restart", "Restart", "F8"),
    ("step", "Step", "F9"),
    ("step_over", "Step Over", "F10"),
    ("config", "Config", "F11"),
)
INSTRUCTION_HEADERS = (
    "#",
    "Address",
    "Bytes",
    "Raw Instruction",
    "Origin",
    "Status",
)
REGISTER_HEADERS = ("Reg", "Hexadecimal", "Decimal")
LOWER_TAB_NAMES = (
    "Stack View",
    "Memory View",
    "Breakpoints",
    "Debug Log",
)
ZONE_HEADERS = ("Start", "End", "Size", "Origin", "Status", "Loaded Bytes")
BREAKPOINT_HEADERS = ("Address", "Name", "Instruction", "Status")
MEMORY_ADDRESS_FILTER = "Search Address"
BREAKPOINT_FILTER = "Search Breakpoint"
LOG_FILTER = "Search Log"
BREAKPOINT_ADDRESS_PLACEHOLDER = (
    "Enter a breakpoint address and press ENTER"
)
MEMORY_SELECTION_TEMPLATE = (
    "Block: 0x{start:08X} - 0x{end:08X} | "
    "Bytes: {size} (0x{size:X})"
)
MEMORY_SELECTION_EMPTY = "Block: - | Bytes: 0 (0x0)"
MEMORY_OUT_OF_RANGE = "Out Of Range"
FOLLOW_LABEL = "Follow:"
FOLLOW_WRITE_LABEL = "W"
FOLLOW_READ_LABEL = "R"
CONFIG_TITLE = "Debugger Config"
CONFIG_INTERVAL_PLACEHOLDER = "Interval (ms)"
CONFIG_CONFIRM = "Confirm"
