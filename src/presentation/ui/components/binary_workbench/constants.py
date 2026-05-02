class BINARY_WORKBENCH_TEXT:
    TITLE: str = "Binary Workbench"
    SUBTITLE: str = (
        "Open, inspect, navigate, version and rebuild binary artifacts."
    )
    STATUS_IDLE: str = "Select a tool action to continue."
    STATUS_PLACEHOLDER_TEMPLATE: str = '"{name}" is not implemented yet.'
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


class BINARY_WORKBENCH_LAYOUT:
    WINDOW_WIDTH: int = 920
    WINDOW_HEIGHT: int = 560
    ROOT_LEFT: int = 0
    ROOT_TOP: int = 0
    ROOT_RIGHT: int = 0
    ROOT_BOTTOM: int = 0
    BODY_LEFT: int = 28
    BODY_TOP: int = 28
    BODY_RIGHT: int = 28
    BODY_BOTTOM: int = 28
    BODY_SPACING: int = 12
