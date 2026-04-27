from src.core.converter.errors import MAX_BYTE_LENGTH


HEX_CHARS = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"}


def display_padding_len(display: str, raw_value: str) -> int:
    compact = "".join(display.split())
    if raw_value and compact.endswith(raw_value):
        return len(compact) - len(raw_value)
    return max(0, len(compact) - len(raw_value))


def raw_index_from_display_position(display: str, raw_value: str, position: int) -> int:
    compact_before_cursor = sum(
        1
        for char in display[:max(0, min(position, len(display)))]
        if not char.isspace()
    )
    padding_len = display_padding_len(display, raw_value)
    return max(0, min(len(raw_value), compact_before_cursor - padding_len))


def display_position_from_raw_index(display: str, raw_value: str, raw_index: int) -> int:
    target_compact_index = display_padding_len(display, raw_value) + max(
        0,
        min(raw_index, len(raw_value)),
    )
    compact_count = 0
    for position, char in enumerate(display):
        if char.isspace():
            continue
        if compact_count >= target_compact_index:
            return position
        compact_count += 1
    return len(display)


def is_valid_char(input_type: str, char: str) -> bool:
    if input_type == "decimal":
        return char.isdigit()
    if input_type == "binary":
        return char in {"0", "1"}
    return char.upper() in HEX_CHARS


def normalize_char(input_type: str, char: str) -> str:
    return char.upper() if input_type in ("hexBE", "hexLE") else char


def within_limit(input_type: str, value: str) -> bool:
    if input_type == "decimal":
        if not value:
            return True
        return max(1, (int(value).bit_length() + 7) // 8) <= MAX_BYTE_LENGTH
    if input_type == "binary":
        return len(value) <= (MAX_BYTE_LENGTH * 8)
    return len(value) <= (MAX_BYTE_LENGTH * 2)
