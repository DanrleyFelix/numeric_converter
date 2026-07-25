"""Safe editing of retained debugger breakpoint metadata."""

from dataclasses import replace

from src.core.debugger.breakpoints.conditions import parse_register_condition
from src.core.debugger.breakpoints.types import (
    DEFAULT_BREAKPOINT_TYPE,
    REGISTER_BREAKPOINT_TYPE,
    breakpoint_type_tokens,
    normalize_breakpoint_type,
    parse_breakpoint_address,
)
from src.core.debugger.models.session import DebuggerBreakpoint, DebuggerEvent


class PsxBreakpointEditingMixin:
    """Apply table edits without letting invalid WHERE values affect execution."""

    def set_breakpoint_enabled(self, identifier: int, enabled: bool) -> None:
        """Preserve breakpoint metadata while changing its active state."""

        current = self._breakpoint_for(identifier)
        if current is None and identifier >= 0:
            current = self.add_breakpoint(identifier, enabled)
        if current is not None:
            self._breakpoints[current.identifier] = replace(
                current, enabled=enabled
            )

    def set_breakpoint_name(self, identifier: int, name: str) -> None:
        """Update only the symbolic name retained for one breakpoint."""

        current = self._breakpoint_for(identifier)
        if current is not None:
            self._breakpoints[current.identifier] = replace(current, name=name)

    def set_breakpoint_type(self, identifier: int, expression: str) -> None:
        """Change Type and revalidate WHERE for the resulting category."""

        current = self._breakpoint_for(identifier)
        if current is None:
            return
        try:
            breakpoint_type = normalize_breakpoint_type(expression)
        except ValueError as error:
            self._record_where_syntax_error(str(error))
            return
        changing_to_register = (
            breakpoint_type == REGISTER_BREAKPOINT_TYPE
            and current.breakpoint_type != REGISTER_BREAKPOINT_TYPE
        )
        updated = replace(
            current,
            breakpoint_type=breakpoint_type,
            address=None if changing_to_register else current.address,
            instruction="-" if changing_to_register else current.instruction,
            hit_instruction="",
            triggered=False,
        )
        if changing_to_register:
            updated = replace(
                updated,
                identifier=self._allocate_breakpoint_identifier(),
            )
        self._apply_where(current, updated, updated.where)

    def set_breakpoint_where(self, identifier: int, expression: str) -> None:
        """Store WHERE and keep malformed expressions inactive."""

        current = self._breakpoint_for(identifier)
        if current is not None:
            self._apply_where(current, current, expression.strip())

    def _apply_where(
        self,
        previous: DebuggerBreakpoint,
        current: DebuggerBreakpoint,
        where: str,
    ) -> None:
        """Validate one staged WHERE edit and persist its safe result."""

        try:
            if current.breakpoint_type == REGISTER_BREAKPOINT_TYPE:
                parse_register_condition(where, self._register_aliases)
                updated = replace(
                    current,
                    address=None,
                    instruction="-",
                    where=where,
                    valid=True,
                )
            else:
                updated = self._address_breakpoint(current, where)
        except ValueError as error:
            updated = replace(
                current,
                address=None,
                instruction="-",
                where=where,
                valid=False,
            )
            self._record_where_syntax_error(str(error))
        self._store_breakpoint(previous.identifier, updated)

    def _address_breakpoint(
        self,
        current: DebuggerBreakpoint,
        where: str,
    ) -> DebuggerBreakpoint:
        """Build validated address metadata from a hexadecimal WHERE value."""

        address = parse_breakpoint_address(where)
        collision = next(
            (
                item
                for item in self._breakpoints.values()
                if item.address == address
                and item.identifier != current.identifier
            ),
            None,
        )
        if collision is not None:
            raise ValueError("address already used by another breakpoint at column 1.")
        instruction = self._instruction_at(address)
        tokens = breakpoint_type_tokens(current.breakpoint_type)
        valid = bool(self._image and self._image.contains(address))
        valid = valid and (
            tokens != frozenset({DEFAULT_BREAKPOINT_TYPE})
            or instruction is not None
        )
        return replace(
            current,
            address=address,
            origin=instruction.origin if instruction else "",
            instruction=instruction.raw_instruction if instruction else "-",
            where=f"0x{address:08X}",
            identifier=address,
            valid=valid,
        )

    def _store_breakpoint(
        self,
        previous_identifier: int,
        breakpoint: DebuggerBreakpoint,
    ) -> None:
        """Replace a breakpoint even when editing changed its identifier."""

        self._breakpoints.pop(previous_identifier, None)
        self._breakpoints[breakpoint.identifier] = breakpoint

    def _allocate_breakpoint_identifier(self) -> int:
        """Reserve one stable non-address identifier."""

        identifier = self._next_breakpoint_identifier
        self._next_breakpoint_identifier -= 1
        return identifier

    def _record_where_syntax_error(self, message: str) -> None:
        """Report malformed WHERE input without changing debugger state."""
        self._events.append(DebuggerEvent("Syntax Error", f"WHERE: {message}"))
