class BINARY_WORKBENCH_ADVANCED_CONFIG_TEXT:
    TITLE: str = "Advanced Configuration"
    CPU_ARCH_LABEL: str = "CPU Arch"
    READ_MODE_LABEL: str = "Read Mode"
    BLOCK_SIZE_LABEL: str = "Block Size"
    CACHE_MAX_BLOCKS_LABEL: str = "Cache Max Blocks"
    SELECTION_LIMIT_LABEL: str = "Selection Limit"
    CONFIRM: str = "Confirm"
    OPTION_PSX_MIPS_R3000A: str = "PSX - Mips R3000A"


class BINARY_WORKBENCH_ADVANCED_CONFIG_LAYOUT:
    CONFIRM_TOP_SPACING: int = 10
    CONTROL_WIDTH: int = 200
    BLOCK_SIZE_OPTIONS: tuple[int, ...] = (256, 512, 1024, 2048, 4096)
    CACHE_MAX_BLOCKS_OPTIONS: tuple[int, ...] = (1000, 2000, 4000, 8000, 16000)


class BINARY_WORKBENCH_BYTES_FORMATTER_TEXT:
    TITLE: str = "Bytes Formatter"
    SUBTITLE: str = "Configure typing and grouping for the active binary context."
    GROUP_BYTES_LABEL: str = "Group Bytes"
    UPPERCASE_BYTES_LABEL: str = "Auto-uppercase Bytes"
    UPPERCASE_INSTRUCTIONS_LABEL: str = "Auto-uppercase Instructions"
    CONFIRM: str = "Confirm"


class BINARY_WORKBENCH_BYTES_FORMATTER_LAYOUT:
    GROUP_BYTES_WIDTH: int = 150
    VERTICAL_SPACING: int = 16
    CONFIRM_TOP_SPACING: int = 10


class BINARY_WORKBENCH_REFERENCE_OFFSETS_LAYOUT:
    VERTICAL_SPACING: int = 16
    CONFIRM_TOP_SPACING: int = 10
    DIALOG_MAX_WIDTH: int = 640
    DIALOG_MAX_HEIGHT: int = 640
    DIALOG_MIN_WIDTH: int = 400


class BINARY_WORKBENCH_RULES_TEXT:
    TITLE: str = "Rules"
    BYTE_SHIFT: str = "Allow byte shifting"
    EDITOR_EDIT: str = "Allow Bytes or Assembly editor editing"
    FREE_AFTER_END: str = "Allow free editing only after the original final offset"
    CONFIRM: str = "Confirm"


class BINARY_WORKBENCH_RULES_LAYOUT:
    MARGIN: int = 20
    VERTICAL_SPACING: int = 16
    CONFIRM_TOP_SPACING: int = 10
