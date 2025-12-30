import binascii
from src.models.constants import REGEX_BINARY_GROUP


class Converter:

    @staticmethod
    def to_hex_be(value: int, byte_length: int = 2) -> str:
        try:
            packed = value.to_bytes(byte_length, byteorder="big", signed=False)
            return " ".join(f"{b:02X}" for b in packed)
        except Exception:
            return "00 00"

    @staticmethod
    def to_hex_le(value: int, byte_length: int = 2) -> str:
        try:
            packed = value.to_bytes(byte_length, byteorder="little", signed=False)
            return " ".join(f"{b:02X}" for b in packed)
        except Exception:
            return "00 00"

    @staticmethod
    def to_binary(value: int) -> str:
        bin_str = bin(value)[2:]
        while len(bin_str) % 4 != 0:
            bin_str = "0" + bin_str
        return " ".join(REGEX_BINARY_GROUP.findall(bin_str))

    @staticmethod
    def from_hex(hex_str: str) -> int:
        return int(hex_str.replace(" ", ""), 16)

    @staticmethod
    def from_binary(bin_str: str) -> int:
        return int(bin_str.replace(" ", ""), 2)

    @staticmethod
    def convert(from_type: str, value: str) -> dict:
        dec = 0
        if from_type == "decimal":
            dec = int(value) if value.isdigit() else 0
        elif from_type == "binary":
            dec = Converter.from_binary(value)
        elif from_type == "hexBE":
            dec = Converter.from_hex(value)
        elif from_type == "hexLE":
            clean = value.replace(" ", "")
            raw = binascii.unhexlify(clean)
            dec = int.from_bytes(raw, byteorder="little")

        return {
            "decimal": str(dec),
            "binary": Converter.to_binary(dec),
            "hexBE": Converter.to_hex_be(dec),
            "hexLE": Converter.to_hex_le(dec)
        }


