from __future__ import annotations

from src.core.binary_workbench.psx_sector_layout import RAW_SECTOR_SIZE, SYNC_HEADER, sector_layout


def rebuild_psx_sector(sector: bytes, sector_index: int) -> bytes:
    layout = sector_layout(sector, len(sector))
    if len(sector) != RAW_SECTOR_SIZE or layout.mode not in {1, 2}:
        return sector
    rebuilt = bytearray(sector)
    rebuilt[:12] = SYNC_HEADER
    _write_header(rebuilt, sector_index)
    if layout.mode == 1:
        rebuilt[2064:2068] = _edc(rebuilt[:2064]).to_bytes(4, "little")
        rebuilt[2068:2076] = b"\x00" * 8
        _write_ecc(rebuilt, zero_header=False)
    elif layout.form == 1:
        rebuilt[2072:2076] = _edc(rebuilt[16:2072]).to_bytes(4, "little")
        _write_ecc(rebuilt, zero_header=True)
    else:
        rebuilt[2348:2352] = _edc(rebuilt[16:2348]).to_bytes(4, "little")
    return bytes(rebuilt)


def _write_header(sector: bytearray, sector_index: int) -> None:
    absolute = sector_index + 150
    minute, remainder = divmod(absolute, 75 * 60)
    second, frame = divmod(remainder, 75)
    sector[12:15] = bytes((_bcd(minute), _bcd(second), _bcd(frame)))


def _bcd(value: int) -> int:
    return ((value // 10) << 4) | (value % 10)


def _edc(data: bytes | bytearray) -> int:
    value = 0
    for byte in data:
        value = (value >> 8) ^ _EDC_LUT[(value ^ byte) & 0xFF]
    return value


def _write_ecc(sector: bytearray, zero_header: bool) -> None:
    header = bytes(sector[12:16])
    if zero_header:
        sector[12:16] = b"\x00" * 4
    sector[2076:2248] = _ecc(sector[12:2076], 86, 24, 2, 86)
    sector[2248:2352] = _ecc(sector[12:2248], 52, 43, 86, 88)
    if zero_header:
        sector[12:16] = header


def _ecc(source: bytes | bytearray, major_count: int, minor_count: int, major_mult: int, minor_inc: int) -> bytes:
    size = major_count * minor_count
    result = bytearray(major_count * 2)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        ecc_a = ecc_b = 0
        for _ in range(minor_count):
            value = source[index]
            index = (index + minor_inc) % size
            ecc_a ^= value
            ecc_b ^= value
            ecc_a = _ECC_F_LUT[ecc_a]
        ecc_a = _ECC_B_LUT[_ECC_F_LUT[ecc_a] ^ ecc_b]
        result[major] = ecc_a
        result[major + major_count] = ecc_a ^ ecc_b
    return bytes(result)


def _ecc_luts() -> tuple[tuple[int, ...], tuple[int, ...]]:
    forward = [0] * 256
    backward = [0] * 256
    for index in range(256):
        value = index << 1
        if value & 0x100:
            value ^= 0x11D
        forward[index] = value
        backward[index ^ value] = index
    return tuple(forward), tuple(backward)


def _edc_lut() -> tuple[int, ...]:
    values: list[int] = []
    for index in range(256):
        value = index
        for _ in range(8):
            value = (value >> 1) ^ (0xD8018001 if value & 1 else 0)
        values.append(value)
    return tuple(values)


_ECC_F_LUT, _ECC_B_LUT = _ecc_luts()
_EDC_LUT = _edc_lut()
