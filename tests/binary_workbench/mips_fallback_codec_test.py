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


def test_mips_codec_keeps_unrecognized_words_as_memory_data():
    """Never let a broader native decoder erase a complete four-byte word."""

    codec = PsxMipsR3000ACodec(use_native_engines=False)

    assert codec.disassemble(bytes.fromhex("FF FF FF FF"), 0) == "word 0xFFFFFFFF"
    assert codec.assemble("word 0xFFFFFFFF", 0) == bytes.fromhex("FF FF FF FF")


def test_mips_codec_canonicalizes_native_negu_alias_to_subu():
    """Raw Instructions must expose the real opcode instead of a pseudo alias."""

    codec = PsxMipsR3000ACodec(use_native_engines=False)
    data = assemble_fallback("subu $a0, $zero, $t3", 0)

    assert codec.disassemble(data, 0) == "subu $a0, $zero, $t3"


def test_mips_fallback_assembles_register_aliases_to_same_bytes():
    assert assemble_fallback("addiu $s1, $zero, 1", 0) == assemble_fallback("addiu r17, $0, 1", 0)
    assert assemble_fallback("lw $t0, 4($sp)", 0) == assemble_fallback("lw $r8, 4(r29)", 0)
    assert assemble_fallback("jr $ra", 0) == assemble_fallback("jr $31", 0)
    assert PsxMipsR3000ACodec().assemble("jr 31", 0) is None
