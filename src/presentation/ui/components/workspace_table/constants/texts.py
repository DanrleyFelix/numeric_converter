class WORKSPACE_TABLE_TEXT:
    VARIABLES_TITLE: str = "Variables"
    LOGS_TITLE: str = "Logs"


WORKSPACE_TABLE_HEADERS: dict[str, list[str]] = {
    "variables": ["Name", "Value", "Hex"],
    "logs": ["Instruction", "Result"],
}
