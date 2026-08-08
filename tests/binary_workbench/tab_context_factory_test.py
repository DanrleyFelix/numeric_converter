from pathlib import Path

from src.modules.binary_workbench_dtos import BinaryWorkbenchStateDTO
from src.presentation.ui.components.binary_workbench.tabs import (
    tab_context_factory as factory,
)


def test_source_only_assembly_open_does_not_run_the_assembler(
    tmp_path: Path,
    monkeypatch,
):
    """Keep large Open File work off the GUI path until viewport derivation."""

    source = tmp_path / "large.asm"
    source.write_text("start:\naddiu $a0, $zero, 2\n", encoding="utf-8")

    def _unexpected_derivation(*_args, **_kwargs):
        raise AssertionError("source-only open must not assemble the full file")

    monkeypatch.setattr(factory, "rows_from_path", _unexpected_derivation)

    context = factory.create_assembly_tab(
        BinaryWorkbenchStateDTO(),
        source,
        derive_rows=False,
    )

    assert [row.instruction for row in context.rows] == [
        "start:",
        "addiu $a0, $zero, 2",
    ]
    assert all(row.bytes_text == "" for row in context.rows)
    assert context.labels == {}
