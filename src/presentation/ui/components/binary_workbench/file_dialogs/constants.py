class BINARY_WORKBENCH_FILE_DIALOG_TEXT:
    LBA_TITLE: str = "LBA File System"
    LBA_SECTOR_LABEL: str = "LBA Sector"
    LBA_JSON_FILTER: str = "JSON files (*.json);;All files (*.*)"
    ENCODING_TABLE_JSON_FILTER: str = "JSON files (*.json);;All files (*.*)"
    OFFSET_REGIONS_JSON_FILTER: str = "JSON files (*.json);;All files (*.*)"
    OFFSET_REGIONS_DEFAULT_FILENAME: str = "Offset Regions.json"
    SYMBOLS_JSON_FILTER: str = "JSON files (*.json);;All files (*.*)"
    INTERNAL_TITLE: str = "Open Internal File"
    VERSION_TITLE: str = "Version"
    VERSION_CREATE_TITLE: str = "Create Version"
    VERSION_CHANGE_TITLE: str = "Change Version"
    VERSION_CHANGE_SUBTITLE: str = "Select the active version for this binary."
    VERSION_UPDATE_TITLE: str = "Att Version"
    VERSION_SUBTITLE: str = "Choose a name for the current version snapshot."
    VERSION_LOAD_TITLE: str = "Load Versions File"
    VERSION_LOAD_SUBTITLE: str = "Select a saved versions file to load into the active binary tab."
    VERSION_JSON_FILTER: str = "JSON files (*.json);;All files (*.*)"
    VERSION_NAME_LABEL: str = "Name"
    CONFIRM: str = "Confirm"
    INTERNAL_NAME_LABEL: str = "Internal file"
    LOAD: str = "Load"
    SAVE: str = "Save"
    OK: str = "OK"


class BINARY_WORKBENCH_VERSION_DIALOG_LAYOUT:
    CREATE_CONFIRM_TOP_SPACING: int = 10
    CHANGE_LIST_SPACING: int = 15
    CHANGE_LIST_MARGIN: int = 15
    ACTION_BUTTON_SPACING: int = 10
    NAME_FIELD_WIDTH: int = 190
    NAME_FIELD_HEIGHT: int = 46
