class PREFERENCES_DIALOG_TEXT:
    TITLE: str = "Preferences"
    SUBTITLE: str = "Configure grouping and zero padding for each converter input."
    FIELD_HEADER: str = "Field"
    GROUP_SIZE_HEADER: str = "Group Size"
    ZERO_PAD_HEADER: str = "Zero Pad"
    CANCEL: str = "Cancel"
    OK: str = "OK"


FIELD_LABELS: dict[str, str] = {
    "decimal": "Decimal",
    "binary": "Binary",
    "hexBE": "Hex (BE)",
    "hexLE": "Hex (LE)",
}
