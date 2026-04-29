class CONVERTER_PANEL_LAYOUT:
    ROOT_SPACING: int = 20
    ROW_SPACING: int = 10
    LABEL_WIDTH: int = 90
    ROOT_MARGIN: int = 0


class CONVERTER_PANEL_SIZE:
    INPUT_MIN_HEIGHT: int = 40


CONVERTER_PANEL_FIELDS: dict[str, str] = {
    "decimal": "Decimal",
    "binary": "Binary",
    "hexBE": "Hex (BE)",
    "hexLE": "Hex (LE)",
}


CONVERTER_PANEL_TEXT = {
    "copy_raw_tooltip": "Copy raw",
}
