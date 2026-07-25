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
    """Parse supported comparisons joined by `&` and `||` without eval."""

    groups = tuple(
        _parse_and_group(group, aliases)
        for group in str(expression).strip().split("||")
    )
    if not groups or any(not group for group in groups):
        raise ValueError("Register breakpoint condition is invalid.")
    return RegisterCondition(groups)


def _parse_and_group(
    expression: str,
    aliases: Mapping[str, str],
) -> tuple[RegisterComparison, ...]:
    """Parse one sequence of AND-connected register comparisons."""

    comparisons = []
    for fragment in expression.split("&"):
        match = COMPARISON.fullmatch(fragment)
        if match is None:
            raise ValueError("Register breakpoint condition is invalid.")
        register, operator, raw_value = match.groups()
        canonical = aliases.get(register.casefold())
        if canonical is None:
            raise ValueError(f"Unknown debugger register: ${register}.")
        base = 16 if raw_value.lower().lstrip("-").startswith("0x") else 10
        comparisons.append(
            RegisterComparison(canonical, operator, int(raw_value, base))
        )
    return tuple(comparisons)
