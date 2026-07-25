"""Safe parsing and evaluation of register breakpoint conditions."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from src.core.debugger.models.session import DebuggerRegister

COMPARISON = re.compile(
    r"\s*\$([A-Za-z0-9_]+)\s*(<=|>=|!=|==|<|>)\s*"
    r"(-?(?:0[xX][0-9A-Fa-f]+|\d+))\s*"
)
OR_SEPARATOR = re.compile(r"\|\||\bor\b", re.IGNORECASE)
AND_SEPARATOR = re.compile(r"&&|(?<!&)&(?!&)|\band\b", re.IGNORECASE)


@dataclass(frozen=True)
class RegisterComparison:
    """Compare one canonical register value against an integer constant."""

    register: str
    operator: str
    value: int

    def evaluate(self, values: Mapping[str, int]) -> bool:
        """Return whether this comparison matches the supplied snapshot."""

        current = values[self.register]
        if self.operator == "==":
            return current == self.value
        if self.operator == "!=":
            return current != self.value
        if self.operator == "<=":
            return current <= self.value
        if self.operator == ">=":
            return current >= self.value
        if self.operator == "<":
            return current < self.value
        return current > self.value


@dataclass(frozen=True)
class RegisterCondition:
    """Represent OR groups containing AND-connected comparisons."""

    groups: tuple[tuple[RegisterComparison, ...], ...]

    def evaluate(self, values: Mapping[str, int]) -> bool:
        """Evaluate AND before OR using one immutable register snapshot."""

        return any(
            all(comparison.evaluate(values) for comparison in group)
            for group in self.groups
        )


def register_aliases(
    descriptors: Iterable[DebuggerRegister],
) -> dict[str, str]:
    """Map canonical register names and aliases to canonical names."""

    aliases: dict[str, str] = {}
    for descriptor in descriptors:
        aliases[descriptor.name.casefold()] = descriptor.name
        aliases.update(
            (alias.casefold(), descriptor.name)
            for alias in descriptor.aliases
        )
    return aliases


def parse_register_condition(
    expression: str,
    aliases: Mapping[str, str],
) -> RegisterCondition:
    """Parse comparisons joined by AND/OR words or symbolic aliases."""

    source = str(expression).strip()
    groups = tuple(
        _parse_and_group(group, aliases, offset)
        for group, offset in _parts(source, OR_SEPARATOR)
    )
    if not groups or any(not group for group in groups):
        raise ValueError("invalid register condition at column 1.")
    return RegisterCondition(groups)


def _parse_and_group(
    expression: str,
    aliases: Mapping[str, str],
    offset: int,
) -> tuple[RegisterComparison, ...]:
    """Parse one sequence of AND-connected register comparisons."""

    comparisons = []
    for fragment, fragment_offset in _parts(
        expression,
        AND_SEPARATOR,
        offset,
    ):
        match = COMPARISON.fullmatch(fragment)
        if match is None:
            leading = len(fragment) - len(fragment.lstrip())
            raise ValueError(
                f"invalid register comparison at column "
                f"{fragment_offset + leading + 1}."
            )
        register, operator, raw_value = match.groups()
        canonical = aliases.get(register.casefold())
        if canonical is None:
            column = fragment_offset + fragment.find("$") + 1
            raise ValueError(
                f"unknown debugger register ${register} at column {column}."
            )
        base = 16 if raw_value.lower().lstrip("-").startswith("0x") else 10
        comparisons.append(
            RegisterComparison(canonical, operator, int(raw_value, base))
        )
    return tuple(comparisons)


def _parts(
    expression: str,
    separator: re.Pattern[str],
    offset: int = 0,
) -> tuple[tuple[str, int], ...]:
    """Split an expression while retaining source offsets for diagnostics."""

    output = []
    start = 0
    while True:
        match = separator.search(expression, start)
        if match is None:
            output.append((expression[start:], offset + start))
            return tuple(output)
        output.append((expression[start:match.start()], offset + start))
        start = match.end()
