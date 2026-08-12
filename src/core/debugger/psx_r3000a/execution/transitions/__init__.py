from __future__ import annotations

from src.core.debugger.psx_r3000a.control.flow import (
    PsxControlFlow,
    PsxExecutionTransition,
    PsxExecutionTransitionKind,
    classify_execution_transition,
)


def record_execution_transition(
    address: int,
    flow: PsxControlFlow | None,
    destination: int,
) -> PsxExecutionTransition:
    """Classify one Unicorn step, which already includes a MIPS delay slot."""

    return classify_execution_transition(address, destination, flow)


def ignored_execution_transition(address: int, destination: int) -> PsxExecutionTransition:
    """Represent one explicit IGNORED operation as a local fallthrough."""

    return PsxExecutionTransition(
        address,
        destination,
        PsxExecutionTransitionKind.IGNORED,
    )
