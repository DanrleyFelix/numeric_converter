from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.debugger.psx_r3000a.control.branches import decode_branch
from src.core.debugger.psx_r3000a.registers import GPR_NAMES


class PsxControlFlowKind(str, Enum):
    """Classify one R3000A control-transfer instruction."""

    BRANCH = "branch"
    JUMP = "jump"
    CALL = "call"
    RETURN = "return"


class PsxExecutionTransitionKind(str, Enum):
    """Describe how execution reached the PC after one logical operation."""

    SEQUENTIAL = "sequential"
    BRANCH_FALLTHROUGH = "branch_fallthrough"
    BRANCH_TAKEN = "branch_taken"
    JUMP = "jump"
    CALL = "call"
    RETURN = "return"
    IGNORED = "ignored"


@dataclass(frozen=True)
class PsxControlFlow:
    """Describe a decoded R3000A control-flow operation."""

    mnemonic: str
    destination: int
    is_call: bool
    kind: PsxControlFlowKind = PsxControlFlowKind.JUMP
    taken: bool = True


@dataclass(frozen=True)
class PsxExecutionTransition:
    """Retain the source, destination and semantic kind of one transition."""

    source: int
    destination: int
    kind: PsxExecutionTransitionKind

    @property
    def permits_entry_completion(self) -> bool:
        """Return whether this transition may naturally end the entry range."""

        return self.kind in {
            PsxExecutionTransitionKind.SEQUENTIAL,
            PsxExecutionTransitionKind.BRANCH_FALLTHROUGH,
            PsxExecutionTransitionKind.IGNORED,
        }


def decode_control_flow(
    data: bytes,
    pc: int,
    registers: dict[str, int],
) -> PsxControlFlow | None:
    """Decode direct and register R3000A control-flow instructions."""

    if len(data) != 4:
        return None
    word = int.from_bytes(data, "little")
    opcode = word >> 26
    if opcode in {2, 3}:
        destination = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        is_call = opcode == 3
        kind = PsxControlFlowKind.CALL if is_call else PsxControlFlowKind.JUMP
        return PsxControlFlow("jal" if is_call else "j", destination, is_call, kind)
    branch = decode_branch(
        word,
        opcode,
        pc,
        registers,
        lambda mnemonic, destination, is_call, kind, taken: PsxControlFlow(
            mnemonic,
            destination,
            is_call,
            PsxControlFlowKind(kind),
            taken,
        ),
    )
    if branch is not None:
        return branch
    if opcode != 0:
        return None
    function = word & 0x3F
    if function not in {8, 9}:
        return None
    register_index = (word >> 21) & 0x1F
    destination = registers.get(GPR_NAMES[register_index], 0)
    mnemonic = "jalr" if function == 9 else "jr"
    is_call = function == 9
    kind = (
        PsxControlFlowKind.CALL
        if is_call
        else PsxControlFlowKind.RETURN
        if register_index == 31
        else PsxControlFlowKind.JUMP
    )
    return PsxControlFlow(mnemonic, destination, is_call, kind)


def classify_execution_transition(
    source: int,
    destination: int,
    flow: PsxControlFlow | None,
) -> PsxExecutionTransition:
    """Classify the completed control transition without consulting UI state."""

    if flow is None:
        kind = PsxExecutionTransitionKind.SEQUENTIAL
    elif flow.kind == PsxControlFlowKind.BRANCH:
        kind = (
            PsxExecutionTransitionKind.BRANCH_TAKEN
            if flow.taken
            else PsxExecutionTransitionKind.BRANCH_FALLTHROUGH
        )
    else:
        kind = PsxExecutionTransitionKind(flow.kind.value)
    return PsxExecutionTransition(source, destination, kind)
