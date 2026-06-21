from dataclasses import dataclass, field
from numbers import Number


def _default_command_variables() -> dict[str, Number]:
    return {"ANS": 0}


@dataclass(frozen=True)
class CommandLogPreferencesDTO:
    enabled: bool = True
    assignment_only: bool = True
    single_unary_only: bool = True
    no_operator: bool = True
    assignment_operator: bool = True
    binary_operator_only: bool = False


@dataclass(frozen=True)
class CommandEntryDTO:
    input: str
    output: str | None


@dataclass(frozen=True)
class CommandRenderResultDTO:
    lines: list[str]
    color: str
    message: str | None = None


@dataclass(frozen=True)
class CommandContextDTO:
    active_line: str = ""
    history: list[CommandEntryDTO] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    variables: dict[str, Number] = field(default_factory=_default_command_variables)
