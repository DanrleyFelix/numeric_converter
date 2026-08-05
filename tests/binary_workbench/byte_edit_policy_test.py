from src.core.binary_workbench.byte_editing import (
    ByteEditViolation,
    ByteRowAccess,
    aligned_source_indices,
    byte_edit_violation,
    byte_lines_ready_for_commit,
    byte_row_policy,
)


def test_source_only_and_annotated_instruction_policies_are_distinct():
    assert byte_row_policy("entry:", False).show_placeholder
    assert byte_row_policy("; note", False).show_placeholder
    assert byte_row_policy("* define $sp 0x801FFFF0", False).show_placeholder
    assert byte_row_policy("* partially_typed_directive", False).show_placeholder
    assert byte_row_policy("entry: nop", True).access is ByteRowAccess.EDITABLE
    assert (
        byte_row_policy("addiu $t0, $zero, 1 ; note", True).access
        is ByteRowAccess.EDITABLE
    )
    assert byte_row_policy("nop", True).removable_from_bytes
    assert not byte_row_policy("entry: nop", True).removable_from_bytes
    assert not byte_row_policy("nop ; note", True).removable_from_bytes
    assert byte_row_policy("", False).removable_from_bytes
    assert not byte_row_policy("; note", False).removable_from_bytes
    assert (
        byte_row_policy("* define $sp 0x801FFFF0", False).access
        is ByteRowAccess.ASSEMBLY_ONLY
    )


def test_byte_edit_validation_allows_only_plain_replacement_and_append():
    policies = (
        byte_row_policy("nop", True),
        byte_row_policy("jr $ra", True),
    )
    assert (
        byte_edit_violation(
            ("00 00 00 00", "01 00 08 24"),
            ("00 00 00 00", "02 00 08 24"),
            policies,
        )
        is ByteEditViolation.NONE
    )
    assert byte_edit_violation(
        ("00 00 00 00", "01 00 08 24"),
        ("00 00 00 00",),
        policies,
    ) is ByteEditViolation.NONE
    assert byte_edit_violation(
        ("00 00 00 00",),
        ("00 00 00 00", "08 00 E0 03"),
        policies[:1],
    ) is ByteEditViolation.NONE


def test_byte_edit_validation_removes_plain_or_empty_assembly_rows():
    previous = ("00 00 00 00", "-", "08 00 E0 03")
    current = ("00 00 00 00", "08 00 E0 03")

    assert byte_edit_violation(
        previous,
        current,
        (
            byte_row_policy("nop", True),
            byte_row_policy("", False),
            byte_row_policy("jr $ra", True),
        ),
    ) is ByteEditViolation.NONE
    assert byte_edit_violation(
        previous,
        current,
        (
            byte_row_policy("nop", True),
            byte_row_policy("; keep", False),
            byte_row_policy("jr $ra", True),
        ),
    ) is ByteEditViolation.ROW_REMOVAL

    assert byte_edit_violation(
        ("-", "00 00 00 00"),
        ("01 00 00 00",),
        (
            byte_row_policy("", False),
            byte_row_policy("entry: nop", True),
        ),
    ) is ByteEditViolation.ROW_REMOVAL


def test_incomplete_byte_lines_are_staged_until_every_changed_row_is_complete():
    previous = ("08 00 A6 AF", "0C 00 A7 AF")

    assert not byte_lines_ready_for_commit(previous, ("08 00 A6 A", *previous[1:]), 4)
    assert byte_lines_ready_for_commit(previous, ("08 00 A6 8F", *previous[1:]), 4)
    assert not byte_lines_ready_for_commit(previous, (*previous, ""), 4)
    assert byte_lines_ready_for_commit(previous, (*previous, "00 00 00 00"), 4)


def test_byte_splice_alignment_preserves_unchanged_suffix_identity():
    assert aligned_source_indices(
        ("AA AA AA AA", "BB BB BB BB", "CC CC CC CC"),
        ("BB BB BB BB", "CC CC CC CC"),
    ) == (1, 2)


def test_byte_splice_uses_the_edited_row_when_byte_lines_are_repeated():
    repeated = ("02 00 84 24",) * 5

    assert aligned_source_indices(
        repeated,
        (*repeated[:2], "00 00 00 00", *repeated[2:]),
        2,
    ) == (0, 1, None, 2, 3, 4)
    assert aligned_source_indices(
        repeated,
        (*repeated[:2], *repeated[3:]),
        2,
    ) == (0, 1, 3, 4)


def test_inserting_before_a_protected_row_does_not_remove_that_row():
    previous = ("02 00 84 24", "", "60 00 BD 27")
    current = ("02 00 84 24", "00 00 00 00", "", "60 00 BD 27")
    policies = (
        byte_row_policy("addiu $a0, $a0, 2", True),
        byte_row_policy("spInit:", False),
        byte_row_policy("addiu $sp, $sp, 0x60", True),
    )

    assert byte_edit_violation(previous, current, policies, 1) is ByteEditViolation.NONE


def test_annotated_source_can_be_replaced_but_directive_cannot():
    for source in ("entry: nop", "nop ; keep", "invalid instruction"):
        assert byte_edit_violation(
            ("00 00 00 00",),
            ("01 00 00 00",),
            (byte_row_policy(source, source != "invalid instruction"),),
        ) is ByteEditViolation.NONE
    assert byte_edit_violation(
        ("",),
        ("01 00 00 00",),
        (byte_row_policy("* define $sp 0x801FFFF0", False),),
    ) is ByteEditViolation.ASSEMBLY_ONLY
