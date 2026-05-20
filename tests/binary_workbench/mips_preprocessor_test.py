from src.core.binary_workbench.mips_r3000a import (
    expand_pseudo_instruction,
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


def test_mips_pseudo_instructions_expand_to_core_instructions():
    assert expand_pseudo_instruction("li $v0, 1") == ["li $v0, 1"]
    assert expand_pseudo_instruction("move $a0, $s1") == ["addu $a0, $s1, $zero"]
    assert expand_pseudo_instruction("loop: b loop") == ["loop: beq $zero, $zero, loop"]


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
