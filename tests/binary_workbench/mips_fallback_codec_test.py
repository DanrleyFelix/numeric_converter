from src.core.binary_workbench.mips_r3000a.assembler import assemble_fallback
from src.core.binary_workbench.mips_r3000a.codec import PsxMipsR3000ACodec
from src.core.binary_workbench.mips_r3000a.disassembler import disassemble_fallback
from src.core.binary_workbench.mips_r3000a.preprocessor import is_core_mips_instruction


def test_mips_preprocessor_accepts_added_core_instructions():
    for instruction in (
        "sll $t0, $t1, 4",
        "srlv $t0, $t1, $t2",
        "mflo $v0",
        "mult $t0, $t1",
        "andi $t0, $t1, 0xFFFF",
        "lwl $t0, -4($sp)",
        "syscall",
    ):
        assert is_core_mips_instruction(instruction)


def test_mips_fallback_assembles_shift_and_hilo_instructions():
    assert assemble_fallback("sll $t0, $t1, 4", 0) == bytes.fromhex("00 41 09 00")
    assert assemble_fallback("srl $s0, $s1, 3", 0) == bytes.fromhex("C2 80 11 00")
    assert assemble_fallback("sllv $t0, $t1, $t2", 0) == bytes.fromhex("04 40 49 01")
    assert assemble_fallback("mult $t0, $t1", 0) == bytes.fromhex("18 00 09 01")
    assert assemble_fallback("mflo $v0", 0) == bytes.fromhex("12 10 00 00")


def test_mips_fallback_assembles_immediate_memory_and_jalr_instructions():
    assert assemble_fallback("andi $t0, $t1, 0xFFFF", 0) == bytes.fromhex("FF FF 28 31")
    assert assemble_fallback("lwl $t0, -4($sp)", 0) == bytes.fromhex("FC FF A8 8B")
    assert assemble_fallback("jalr $t0, $t1", 0) == bytes.fromhex("09 40 20 01")


def test_mips_fallback_disassembles_supported_operand_families():
    cases = {
        0x00094100: "sll $t0, $t1, 0x4",
        0x001180C2: "srl $s0, $s1, 0x3",
        0x01494004: "sllv $t0, $t1, $t2",
        0x01090018: "mult $t0, $t1",
        0x00001012: "mflo $v0",
        0x3128FFFF: "andi $t0, $t1, 0xFFFF",
        0x8BA8FFFC: "lwl $t0, -0x4($sp)",
        0x01204009: "jalr $t0, $t1",
        0x0120F809: "jalr $t1",
    }

    for word, instruction in cases.items():
        assert disassemble_fallback(word, 0) == instruction


def test_mips_codec_routes_jalr_words_to_fallback_even_with_capstone():
    codec = PsxMipsR3000ACodec()
    codec._capstone = object()  # type: ignore[attr-defined]

    assert codec.disassemble(bytes.fromhex("09 F8 20 01"), 0) == "jalr $t1"