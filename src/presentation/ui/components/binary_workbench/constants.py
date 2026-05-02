class BINARY_WORKBENCH_TEXT:
    TITLE: str = "Binary Workbench"
    STATUS_IDLE: str = "Ready."
    STATUS_PLACEHOLDER_TEMPLATE: str = '"{name}" is not implemented yet.'
    STATUS_OPENED_TEMPLATE: str = 'Opened "{name}".'
    STATUS_CLOSED_TEMPLATE: str = 'Closed "{name}".'
    STATUS_INTERNAL_SOURCE_REQUIRED: str = (
        "Select a file-backed tab before opening an internal file."
    )
    FILE: str = "File"
    ENVIRONMENT: str = "Environment"
    PREFERENCES: str = "Preferences"
    SEARCH: str = "Search"
    HELP: str = "Help"
    OPEN_BINARY: str = "Open Binary"
    OPEN_ASSEMBLY_CODE: str = "Open Assembly / Code"
    NEW_SCRATCH_CODE: str = "New Scratch Code"
    OPEN_INTERNAL_FILE: str = "Open Internal File"
    CREATE_VERSION: str = "Create a Version"
    ATT_CURRENT_VERSION: str = "Att Current Version"
    LOAD_VERSION: str = "Load a Version"
    SAVE_BINARY_FILE: str = "Save Binary File"
    SYMBOLS: str = "Symbols"
    REGIONS: str = "Memory Regions"
    LBA_FILESYSTEM: str = "LBA File System"
    LABELS: str = "Labels"
    ENCODING_TABLES: str = "Encoding Tables"
    CPU_ARCH: str = "CPU Arch"
    NAVIGATION_MODE: str = "Navigation Mode"
    VIEW: str = "View"
    ADVANCED_CONFIGURATION: str = "Advanced Configuration"
    BYTES_FORMATTER: str = "Bytes Formatter"
    REFERENCE_OFFSETS: str = "Reference Offsets"
    VISIBLE_COLUMNS: str = "Visible Columns"
    HEX_VIEW: str = "Hex View"
    GO_TO: str = "Go to"
    FIND: str = "Find"
    REPLACE: str = "Replace"
    SELECT_BLOCK: str = "Select Block"
    SELECT_ALL: str = "Select All"
    OFFSET_REFS: str = "Offset refs:"
    FILE_OFFSET: str = "File"
    RAM_OFFSET: str = "RAM"
    SLUS_OFFSET: str = "SLUS"
    INSTRUCTION: str = "Instruction"
    BYTES: str = "Bytes"
    SELECTION_EMPTY: str = "Selected: none | Length: 0 bytes"
    FILE_FILTER_BINARY: str = "Binary files (*.*)"
    FILE_FILTER_ASSEMBLY: str = "Assembly / code files (*.asm *.s *.txt *.c *.cpp *.*)"


class BINARY_WORKBENCH_TAB_KIND:
    BINARY: str = "binary"
    ASSEMBLY: str = "assembly"
    SCRATCH: str = "scratch"
    INTERNAL: str = "internal"


class BINARY_WORKBENCH_LAYOUT:
    WINDOW_WIDTH: int = 920
    WINDOW_HEIGHT: int = 560
    MIN_WIDTH: int = 720
    MIN_HEIGHT: int = 460
    ROOT_LEFT: int = 0
    ROOT_TOP: int = 0
    ROOT_RIGHT: int = 0
    ROOT_BOTTOM: int = 0
    BODY_LEFT: int = 28
    BODY_TOP: int = 28
    BODY_RIGHT: int = 28
    BODY_BOTTOM: int = 28
    BODY_SPACING: int = 12
    TAB_SPACING: int = 12
    OFFSET_BAR_LEFT: int = 14
    OFFSET_BAR_TOP: int = 10
    OFFSET_BAR_RIGHT: int = 14
    OFFSET_BAR_BOTTOM: int = 10
