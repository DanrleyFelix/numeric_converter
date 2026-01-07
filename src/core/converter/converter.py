import binascii


class Converter:

    @staticmethod
    def to_hex_be(value: int, byte_length: int = 2) -> bytes:
        return value.to_bytes(byte_length, byteorder="big", signed=False)

    @staticmethod
    def to_hex_le(value: int, byte_length: int = 2) -> bytes:
        return value.to_bytes(byte_length, byteorder="little", signed=False)

    @staticmethod
    def to_binary(value: int) -> str:
        return bin(value)[2:]

    @staticmethod
    def from_hex(hex_str: str, little_endian: bool = False) -> int:
        clean = hex_str.replace(" ", "")
        raw = binascii.unhexlify(clean)
        byteorder = "little" if little_endian else "big"
        return int.from_bytes(raw, byteorder=byteorder)

    @staticmethod
    def from_binary(bin_str: str) -> int:
        clean = bin_str.replace(" ", "")
        return int(clean, 2)

    @staticmethod
    def convert(from_type: str, value: str) -> dict:
        dec = 0

        if from_type == "decimal":
            dec = int(value) if value.isdigit() else 0
        elif from_type == "binary":
            dec = Converter.from_binary(value)
        elif from_type == "hexBE":
            dec = Converter.from_hex(value, little_endian=False)
        elif from_type == "hexLE":
            dec = Converter.from_hex(value, little_endian=True)

        return {
            "decimal": dec,
            "binary": Converter.to_binary(dec),
            "hexBE": Converter.to_hex_be(dec),
            "hexLE": Converter.to_hex_le(dec)}
