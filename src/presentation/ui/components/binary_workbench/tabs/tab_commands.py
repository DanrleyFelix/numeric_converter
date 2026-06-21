from __future__ import annotations

from pathlib import Path

from src.core.binary_workbench.editor.commands.payloads import commands_from_payload
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.modules.utils import read_json, write_json
from src.presentation.repository.binary_workbench_workspace.constants import COMMANDS
from src.presentation.repository.binary_workbench_workspace.payloads import (
    commands_payload,
)
from src.presentation.ui.components.binary_workbench.editor import BinaryWorkbenchEditorPage


class TabCommandsMixin:
    def custom_commands_for_current_context(self) -> dict[str, list[str]]:
        current = self.current_context()
        return dict(current.custom_commands) if current is not None else {}

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
        self._set_current_commands(
            BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "custom_commands": {**current.custom_commands, **loaded},
                    "module_directories": {
                        **current.module_directories,
                        COMMANDS: str(path.parent),
                    },
                }
            )
        )
        return True

    def save_custom_commands_to_path(self, path: Path) -> Path | None:
        current = self.current_context()
        if current is None:
            return None
        target = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
        write_json(target, commands_payload(target.stem, current.custom_commands))
        self._set_current_commands(
            BinaryWorkbenchTabContextDTO(
                **{
                    **current.__dict__,
                    "module_paths": {
                        **current.module_paths,
                        COMMANDS: str(target),
                    },
                    "module_directories": {
                        **current.module_directories,
                        COMMANDS: str(target.parent),
                    },
                }
            )
        )
        return target

    def replace_custom_command(self, name: str, instructions: list[str]) -> bool:
        page = self.currentWidget()
        if not isinstance(page, BinaryWorkbenchEditorPage):
            return False
        return page.replace_custom_command(name, instructions)

    def remove_custom_command(self, name: str) -> bool:
        page = self.currentWidget()
        if not isinstance(page, BinaryWorkbenchEditorPage):
            return False
        return page.remove_custom_command(name)

    def _set_current_commands(self, context: BinaryWorkbenchTabContextDTO) -> None:
        self._replace_context(context.tab_id, context)
        page = self.currentWidget()
        if isinstance(page, BinaryWorkbenchEditorPage):
            command_directory = context.module_directories.get(COMMANDS)
            page.set_command_directory(Path(command_directory) if command_directory else None)
            page.set_custom_commands(context.custom_commands)
