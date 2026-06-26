from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from src.core.binary_workbench.editor.commands.payloads import (
    commands_from_context,
    commands_from_payload,
    commands_payload,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_STATE
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchStateDTO,
    BinaryWorkbenchTabContextDTO,
)
from src.modules.utils import read_json, write_json
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage
from src.presentation.ui.components.binary_workbench.tabs.tab_state_payload import (
    state_payload,
)


class TabCommandsMixin:
    def custom_commands_for_current_context(self) -> dict[str, list[str]]:
        current = self.current_context()
        return self._commands_for_context(current) if current is not None else {}

    def load_custom_commands_from_path(self, path: Path) -> bool:
        loaded = {
            command.name: list(command.instructions)
            for command in commands_from_payload(read_json(path))
        }
        if not loaded:
            return False
        current = self.current_context()
        if current is None:
            return False
        self._replace_commands_for_arch(
            current.cpu_arch,
            {**self._commands_for_context(current), **loaded},
        )
        return True

    def save_custom_commands_to_path(self, path: Path) -> Path | None:
        current = self.current_context()
        if current is None:
            return None
        target = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
        write_json(target, commands_payload(commands_from_context(self._commands_for_context(current))))
        self.set_directory(BINARY_WORKBENCH_STATE.COMMANDS_DIRECTORY, target.parent)
        return target

    def replace_custom_command(self, name: str, instructions: list[str]) -> bool:
        page = self.currentWidget()
        if not isinstance(page, BinaryWorkbenchEditorPage):
            return False
        if not page.replace_custom_command(name, instructions):
            return False
        self._replace_commands_for_arch(page.current_context().cpu_arch, page.current_context().custom_commands)
        return True

    def remove_custom_command(self, name: str) -> bool:
        page = self.currentWidget()
        if not isinstance(page, BinaryWorkbenchEditorPage):
            return False
        if not page.remove_custom_command(name):
            return False
        self._replace_commands_for_arch(page.current_context().cpu_arch, page.current_context().custom_commands)
        return True

    def _set_current_commands(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._replace_commands_for_arch(context.cpu_arch, context.custom_commands)

    def _commands_for_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> dict[str, list[str]]:
        return {
            name: list(lines)
            for name, lines in self._state.commands_by_arch.get(
                context.cpu_arch,
                context.custom_commands,
            ).items()
        }

    def _replace_commands_for_arch(
        self,
        arch: str,
        commands: dict[str, list[str]],
    ) -> None:
        normalized = {name: list(lines) for name, lines in commands.items()}
        self._state = BinaryWorkbenchStateDTO(
            **{
                **state_payload(self._state),
                "commands_by_arch": {
                    **self._state.commands_by_arch,
                    arch: normalized,
                },
                "tabs": [
                    replace(tab, custom_commands=normalized)
                    if tab.cpu_arch == arch
                    else tab
                    for tab in self._state.tabs
                ],
            }
        )
        self._refresh_command_pages(arch, normalized)
        self.stateChanged.emit(self._state)

    def _refresh_command_pages(
        self,
        arch: str,
        commands: dict[str, list[str]],
    ) -> None:
        for index, context in enumerate(self._state.tabs):
            if context.cpu_arch != arch:
                continue
            page = self.widget(index)
            if isinstance(page, BinaryWorkbenchEditorPage):
                page.replace_context(context)
                page.grid.set_custom_commands(commands)

    def _sync_universal_commands_from_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        commands = {name: list(lines) for name, lines in context.custom_commands.items()}
        current = self._state.commands_by_arch.get(context.cpu_arch, {})
        if commands == current:
            return context
        self._replace_commands_for_arch(context.cpu_arch, commands)
        return replace(context, custom_commands=commands)

    def _context_with_universal_commands(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> BinaryWorkbenchTabContextDTO:
        commands = self._state.commands_by_arch.get(context.cpu_arch)
        if not commands:
            return context
        return replace(
            context,
            custom_commands={name: list(lines) for name, lines in commands.items()},
        )
