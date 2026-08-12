from src.core.binary_workbench.mips_r3000a.editor_commands import editor_command_output
from src.core.binary_workbench.mips_r3000a import (
    build_rows_from_instructions,
    extract_labels_from_instructions,
    expand_pseudo_instruction,
    PsxMipsR3000ACodec,
    preprocess_instruction,
    raw_mips_instruction,
    validate_mips_hazards,
)
from src.core.binary_workbench.mips_r3000a.symbol_resolver import MipsSymbolResolver


def test_mips_preprocessor_resolves_symbols_and_removes_noise():
    labels = {"loop": "0x00000010"}
    variables = {"hp": "20"}
    equates = {"base": "0x34"}

    assert (
        preprocess_instruction(
            "loop: addiu $s1, $zero, _hp ; comment",
            0x80010000,
            labels,
            variables,
            equates,
        )
        == "addiu $s1, $zero, 20"
    )
    assert raw_mips_instruction("j loop", 0x80010004, labels, variables, equates) == "j 0xf810"
    assert raw_mips_instruction("nop", 0x80010008, labels, variables, equates) == "nop"
    assert raw_mips_instruction("li $v0, 1", 0x80010008, labels, variables, equates) == "addiu $v0, $zero, 1"


def test_mips_preprocessor_replaces_only_complete_symbol_tokens():
    symbols = {
        "boost_equip": "0x10",
        "boost_equip_2": "0x20",
    }

    assert preprocess_instruction(
        "addiu $s0, $s0, @boost_equip_2",
        0,
        {},
        symbols,
        symbols,
    ) == "addiu $s0, $s0, 0x20"
    assert preprocess_instruction(
        "addiu $s0, $s0, @boost_equip",
        0,
        {},
        symbols,
        symbols,
    ) == "addiu $s0, $s0, 0x10"


def test_mips_preprocessor_expands_short_destination_forms_for_raw_output():
    assert raw_mips_instruction("addiu $a0, 0x5", 0, {}, {}, {}) == "addiu $a0, $a0, 0x5"
    assert raw_mips_instruction("and $s0, $a0", 4, {}, {}, {}) == "and $s0, $s0, $a0"

    rows = build_rows_from_instructions(
        ["addiu $a0, 0x5", "and $s0, $a0"],
        ["File"],
    )

    assert [row.instruction for row in rows] == ["addiu $a0, 0x5", "and $s0, $a0"]
    assert [row.bytes_text for row in rows] == ["05 00 84 24", "24 80 04 02"]


def test_mips_navigation_targets_require_jump_or_branch_operand():
    codec = PsxMipsR3000ACodec()
    symbols = {"loop": "0x00000010"}

    assert codec.jump_navigation_target("loop: nop", "loop", symbols) is None
    assert codec.jump_navigation_target("j loop", "loop", symbols) == 0x10
    assert codec.jump_navigation_target("beq $zero, $zero, loop", "loop", symbols) == 0x10
    assert codec.jump_navigation_target("bgez $s1, 0x00000020", "0x00000020", symbols) == 0x20
    assert codec.jump_navigation_target("beq $zero, loop, 0x00000020", "loop", symbols) is None


def test_mips_jump_labels_are_adjusted_only_for_assembler_input():
    labels = {"label_teste": "0x1D9200"}
    symbols = {"jump_symbol": "0x1D9200"}

    assert preprocess_instruction("j label_teste", 0, labels, {}, {}) == "j 0x1e8a00"
    assert preprocess_instruction("jal label_teste", 0, labels, {}, {}) == "jal 0x1e8a00"
    assert raw_mips_instruction("j label_teste", 0, labels, {}, {}) == "j 0x1e8a00"
    assert preprocess_instruction("jal @jump_symbol", 0, {}, symbols, symbols) == "jal 0x1D9200"
    assert raw_mips_instruction("jal @jump_symbol", 0, {}, symbols, symbols) == "jal 0x1d9200"
    assert (
        preprocess_instruction(
            "jal absolute_label",
            0x8000F860,
            {"absolute_label": "0x8000F800"},
            {},
            {},
            MipsSymbolResolver(
                {"absolute_label": "0x8000F800"},
                jump_file_offset_base=0,
            ),
        )
        == "jal 0x8000f800"
    )
    assert (
        preprocess_instruction(
            "beq $zero, $zero, label_teste",
            0x1D91F0,
            labels,
            {},
            {},
        )
        == "beq $zero, $zero, 0x0003"
    )


def test_mips_partial_jump_does_not_invoke_the_native_assembler():
    """Avoid Keystone stderr noise while a J/JAL operand is still being typed."""

    calls: list[tuple[int, int]] = []

    class NativeAssemblerProbe:
        """Record native engine construction without performing assembly."""

        KS_ARCH_MIPS = 1
        KS_MODE_MIPS32 = 2
        KS_MODE_LITTLE_ENDIAN = 4

        @staticmethod
        def Ks(architecture: int, mode: int):
            calls.append((architecture, mode))
            raise AssertionError("partial jumps must not reach Keystone")

    codec = PsxMipsR3000ACodec(use_native_engines=False)
    codec._keystone = NativeAssemblerProbe

    assert codec.assemble("j", 0) is None
    assert codec.assemble("jal", 0) is None
    assert calls == []


def test_mips_source_rows_encode_variables_and_equates_from_raw_instructions():
    rows = build_rows_from_instructions(
        [
            "lw $v0, _actor_hp",
            "addiu $v1, $zero, @max_hp",
        ],
        ["File"],
        variables={"actor_hp": "0x2CD($gp)"},
        equates={"max_hp": "0x64"},
    )

    assert [row.offsets["File"] for row in rows] == ["0x00000000", "0x00000004"]
    assert [row.bytes_text for row in rows] == ["CD 02 82 8F", "64 00 03 24"]


def test_mips_pseudo_instructions_expand_to_core_instructions():
    assert expand_pseudo_instruction("li $v0, 1") == ["addiu $v0, $zero, 1"]
    assert expand_pseudo_instruction("move $a0, $s1") == ["addu $a0, $s1, $zero"]
    assert expand_pseudo_instruction("loop: b loop") == ["loop: beq $zero, $zero, loop"]
    assert expand_pseudo_instruction("neg $a0, $t3") == ["sub $a0, $zero, $t3"]
    assert expand_pseudo_instruction("negu $a0, $t3") == ["subu $a0, $zero, $t3"]




def test_mips_li_command_uses_single_addiu_for_16_bit_immediate():
    assert editor_command_output("li", ["0xFFFF", "v0"]) == ["addiu $v0, $zero, 0xFFFF"]
    assert editor_command_output("li", ["0xFFFF", "$v0"]) == ["addiu $v0, $zero, 0xFFFF"]


def test_mips_editor_commands_emit_registers_with_dollar_sign_without_requiring_it():
    assert editor_command_output("lw", ["0x80010010", "4", "s0", "$v0"]) == [
        "lui $s0, 0x8001",
        "ori $s0, $s0, 0xC",
        "lw $v0, 0x4($s0)",
    ]
    assert editor_command_output("blt", ["s1", "$s2", "target"]) == [
        "slt $t0, $s1, $s2",
        "bne $t0, $zero, target",
        "nop",
    ]
    assert editor_command_output("where", ["s1<s2", "4"]) == [
        "where_001_start: slt $t0, $s1, $s2",
        "beq $t0, $zero, where_001_end",
        "nop",
        "# loop body stays here",
        "addiu $s1, $s1, 0x4",
        "beq $zero, $zero, where_001_start",
        "nop",
        "where_001_end: nop",
    ]

def test_mips_source_lines_only_advance_offsets_for_valid_instructions():
    rows = build_rows_from_instructions(
        ["; comment", "entry:", "", "nop", "; next", "jr $ra"],
        ["File"],
    )

    assert [row.offsets["File"] for row in rows] == [
        "-",
        "-",
        "-",
        "0x00000000",
        "-",
        "0x00000004",
    ]
    assert [row.bytes_text for row in rows] == [
        "",
        "",
        "",
        "00 00 00 00",
        "",
        "08 00 E0 03",
    ]
    assert extract_labels_from_instructions(["entry:", "; comment", "nop"]) == {
        "entry": "0x00000000"
    }


def test_mips_invalid_source_line_does_not_advance_following_label():
    rows = build_rows_from_instructions(
        ["nop", "invalid instruction", "next:", "jr $ra"],
        ["File"],
    )

    assert [row.offsets["File"] for row in rows] == [
        "0x00000000",
        "-",
        "-",
        "0x00000004",
    ]
    assert extract_labels_from_instructions(
        ["nop", "invalid instruction", "next:", "jr $ra"]
    ) == {"next": "0x00000004"}


def test_mips_hazard_validator_reports_load_use_and_jump_sequence():
    hazards = validate_mips_hazards(
        [
            "lw $s1, 0($s0)",
            "addiu $s2, $s1, 1",
            "j 0x80010000",
            "jal 0x80010010",
        ]
    )

    assert [(item.line_index, item.severity) for item in hazards] == [(1, "warning"), (3, "error")]

    alias_hazards = validate_mips_hazards(["lw $2, 0($s0)", "bne $v0, $zero, 0x10"])

    assert [(item.line_index, item.severity) for item in alias_hazards] == [(1, "warning")]

def test_mips_preprocessor_accepts_hash_but_does_not_strip_double_slash():
    labels = {"loop": "0x00000010"}

    assert preprocess_instruction("loop: addiu r17, $0, 1 # comment", 0, labels, {}, {}) == "addiu r17, $0, 1"
    assert raw_mips_instruction("addiu $r17, $0, 1 // comment", 0, labels, {}, {}) == "addiu $r17, $0, 1 // comment"
