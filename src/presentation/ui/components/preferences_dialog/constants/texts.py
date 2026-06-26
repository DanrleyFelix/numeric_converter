class PREFERENCES_DIALOG_TEXT:
    TITLE: str = "Preferences"
    SUBTITLE: str = "Configure grouping and zero padding for each converter input."
    DEFAULT_COPY_LABEL: str = "Alt+C Default"
    FIELD_HEADER: str = "Field"
    GROUP_SIZE_HEADER: str = "Group Size"
    ZERO_PAD_HEADER: str = "Zero Pad"
    CANCEL: str = "Cancel"
    OK: str = "OK"


class LOG_PREFERENCES_TEXT:
    TITLE: str = "Logs"
    SUBTITLE: str = "Configure which successful Command Window expressions are saved."
    ENABLED: str = "Enable logs"
    ASSIGNMENT_ONLY: str = "Log expressions that only use = assignment"
    SINGLE_UNARY_ONLY: str = "Log expressions that only use one unary operator"
    NO_OPERATOR: str = "Log expressions without operators"
    ASSIGNMENT_OPERATOR: str = "Log expressions that include = assignment"
    BINARY_OPERATOR_ONLY: str = "Log only expressions with one or more binary operators"
    CANCEL: str = "Cancel"
    OK: str = "OK"


FIELD_LABELS: dict[str, str] = {
    "decimal": "Decimal",
    "binary": "Binary",
    "hexBE": "Hex (BE)",
    "hexLE": "Hex (LE)",
}
