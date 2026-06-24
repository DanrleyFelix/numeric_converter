class BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT:
    TITLE: str = "Advanced Configuration"
    CPU_ARCH_LABEL: str = "CPU Arch"
    READ_MODE_LABEL: str = "Read Mode"
    BLOCK_SIZE_LABEL: str = "Block Size"
    CACHE_MAX_BLOCKS_LABEL: str = "Cache Max Blocks"
    SELECTION_LIMIT_LABEL: str = "Selection Limit"
    CONFIRM: str = "Confirm"


class BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT:
    DIALOG_WIDTH: int = 320
    CONTROL_WIDTH: int = 260
    MARGIN: int = 20
    ITEM_SPACING: int = 6
    CONFIRM_SPACER_HEIGHT: int = 18


class BINARY_WORKBENCH_BYTES_FORMATTER_TEXT:
    TITLE: str = "Bytes Formatter"
    SUBTITLE: str = "Configure typing and grouping for the active binary context."
    GROUP_BYTES_LABEL: str = "Group Bytes"
    UPPERCASE_BYTES_LABEL: str = "Auto-uppercase Bytes"
    UPPERCASE_INSTRUCTIONS_LABEL: str = "Auto-uppercase Instructions"
    CONFIRM: str = "Confirm"


class BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT:
    MARGIN: int = 20
    LAYOUT_SPACING: int = 0
    FIELD_SPACING: int = 16
    IDENTICAL_ITEM_SPACING: int = 15
    CONFIRM_TOP_SPACING: int = 30
    CONTROL_WIDTH: int = 140


class BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT:
    MAX_ROWS: int = 3
    MARGIN: int = 20
    LAYOUT_SPACING: int = 0
    HORIZONTAL_SPACING: int = 15
    IDENTICAL_ITEM_SPACING: int = 15
    CONFIRM_TOP_SPACING: int = 30
    DIALOG_WIDTH: int = 424
    DIALOG_MAX_HEIGHT: int = 640
    CONTROL_WIDTH: int = 140


class BINARY_WORKBENCH_RULES_TEXT:
    TITLE: str = "Rules"
    BYTE_SHIFT: str = "Allow byte shifting"
    EDITOR_EDIT: str = "Allow Bytes or Assembly editor editing"
    FREE_AFTER_END: str = "Allow free editing only after the original final offset"
    CONFIRM: str = "Confirm"


class BINARY_WORKBENCH_RULES_LAYOUT:
    MARGIN: int = 20
    LAYOUT_SPACING: int = 0
    IDENTICAL_ITEM_SPACING: int = 15
    CONFIRM_TOP_SPACING: int = 30
