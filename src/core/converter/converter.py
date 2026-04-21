import binascii
import sys

from src.core.converter.errors import ConverterValidationError, MAX_BYTE_LENGTH

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


class Converter:

    @staticmethod
    def to_hex_be(value: int, byte_length: int | None = None) -> bytes:
        byte_length = Converter._resolve_byte_length(value, byte_length)
        return value.to_bytes(byte_length, byteorder="big", signed=False)

    @staticmethod
    def to_hex_le(value: int, byte_length: int | None = None) -> bytes:
        byte_length = Converter._resolve_byte_length(value, byte_length)
        return value.to_bytes(byte_length, byteorder="little", signed=False)

    @staticmethod
    def to_binary(value: int) -> str:
        if value < 0:
            raise ConverterValidationError("Negative values are not supported.")
        return bin(value)[2:]

    @staticmethod
    def from_hex(hex_str: str, little_endian: bool = False) -> int:
        clean = Converter._normalize(hex_str)
        if not clean:
            return 0
        if len(clean) % 2 != 0:
            raise ConverterValidationError("Hex input must contain a whole number of bytes.")
        Converter._validate_byte_length(len(clean) // 2)
        try:
            raw = binascii.unhexlify(clean)
        except binascii.Error as error:
            raise ConverterValidationError("Invalid hexadecimal input.") from error
        byteorder = "little" if little_endian else "big"
        return int.from_bytes(raw, byteorder=byteorder)

    @staticmethod
    def from_binary(bin_str: str) -> int:
        clean = Converter._normalize(bin_str)
        if not clean:
            return 0
        if any(char not in "01" for char in clean):
            raise ConverterValidationError("Binary input accepts only 0 and 1.")
        Converter._validate_byte_length(max(1, (len(clean) + 7) // 8))
        return int(clean, 2)

    @staticmethod
    def convert(from_type: str, value: str) -> dict:
        clean = Converter._normalize(value)
        if from_type == "decimal":
            dec = Converter._parse_decimal(clean)
            byte_length = Converter._resolve_byte_length(dec)
        elif from_type == "binary":
            dec = Converter.from_binary(clean)
            byte_length = max(1, (len(clean) + 7) // 8) if clean else 1
        elif from_type == "hexBE":
            dec = Converter.from_hex(clean, little_endian=False)
            byte_length = (len(clean) // 2) if clean else 1
        elif from_type == "hexLE":
            dec = Converter.from_hex(clean, little_endian=True)
            byte_length = (len(clean) // 2) if clean else 1
        else:
            raise ConverterValidationError(f"Unsupported source type: {from_type}")

        return {
            "decimal": dec,
            "binary": Converter.to_binary(dec),
            "hexBE": Converter.to_hex_be(dec, byte_length),
            "hexLE": Converter.to_hex_le(dec, byte_length)}

    @staticmethod
    def _normalize(value: str) -> str:
        return value.replace(" ", "").strip()

    @staticmethod
    def _parse_decimal(value: str) -> int:
        if not value:
            return 0
        if not value.isdigit():
            raise ConverterValidationError("Decimal input accepts only digits.")
        parsed = int(value)
        Converter._resolve_byte_length(parsed)
        return parsed

    @staticmethod
    def _resolve_byte_length(value: int, byte_length: int | None = None) -> int:
        if value < 0:
            raise ConverterValidationError("Negative values are not supported.")

        resolved = byte_length
        if resolved is None:
            resolved = max(1, (value.bit_length() + 7) // 8)

        Converter._validate_byte_length(resolved)
        if value >= (1 << (resolved * 8)):
            raise ConverterValidationError(
                f"Value does not fit into {resolved} byte(s)."
            )
        return resolved

    @staticmethod
    def _validate_byte_length(byte_length: int) -> None:
        if byte_length < 1:
            raise ConverterValidationError("Byte length must be at least 1.")
        if byte_length > MAX_BYTE_LENGTH:
            raise ConverterValidationError(
                f"Byte length exceeds the supported limit of {MAX_BYTE_LENGTH} bytes."
            )
