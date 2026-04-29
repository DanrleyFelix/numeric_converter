class CONVERTER_TYPE:
    DECIMAL: str = "decimal"
    BINARY: str = "binary"
    HEX_BE: str = "hexBE"
    HEX_LE: str = "hexLE"


class CONVERTER_FIELD_KEYS:
    ALL: tuple[str, ...] = (
        CONVERTER_TYPE.DECIMAL,
        CONVERTER_TYPE.BINARY,
        CONVERTER_TYPE.HEX_BE,
        CONVERTER_TYPE.HEX_LE,
    )
