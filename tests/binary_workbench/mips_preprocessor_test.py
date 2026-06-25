from src.core.binary_workbench.mips_r3000a import (
    build_rows_from_instructions,
    extract_labels_from_instructions,
    expand_pseudo_instruction,
    PsxMipsR3000ACodec,
    preprocess_instruction,
    raw_mips_instruction,
    validate_mips_hazards,
)


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
    assert raw_mips_instruction("j loop", 0x80010004, labels, variables, equates) == "j 0x80010010"
    assert raw_mips_instruction("nop", 0x80010008, labels, variables, equates) == "nop"
    assert raw_mips_instruction("li $v0, 1", 0x80010008, labels, variables, equates) == "addiu $v0, $zero, 1"


def test_mips_navigation_targets_require_jump_or_branch_operand():
    codec = PsxMipsR3000ACodec()
    symbols = {"loop": "0x00000010"}

    assert codec.jump_navigation_target("loop: nop", "loop", symbols) is None
    assert codec.jump_navigation_target("j loop", "loop", symbols) == 0x10
    assert codec.jump_navigation_target("beq $zero, $zero, loop", "loop", symbols) == 0x10
    assert codec.jump_navigation_target("bgez $s1, 0x00000020", "0x00000020", symbols) == 0x20
    assert codec.jump_navigation_target("beq $zero, loop, 0x00000020", "loop", symbols) is None


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
    assert expand_pseudo_instruction("li $v0, 1") == ["li $v0, 1"]
    assert expand_pseudo_instruction("move $a0, $s1") == ["addu $a0, $s1, $zero"]
    assert expand_pseudo_instruction("loop: b loop") == ["loop: beq $zero, $zero, loop"]


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
