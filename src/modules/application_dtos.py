from dataclasses import dataclass, field

from src.modules.command_window_dtos import CommandContextDTO, CommandLogPreferencesDTO
from src.modules.converter_dtos import ConverterStateDTO, FormattingOutputDTO
from src.modules.shared_dtos import WindowSizeDTO


def _default_formatter_preferences() -> dict[str, FormattingOutputDTO]:
    return {
        "decimal": FormattingOutputDTO(4, True),
        "binary": FormattingOutputDTO(4, True),
        "hexBE": FormattingOutputDTO(2, True),
        "hexLE": FormattingOutputDTO(2, True),
    }


@dataclass(frozen=True)
class ProgramContextDTO:
    recent_files: list[str] = field(default_factory=list)
    last_binary_workspaces: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ApplicationContextDTO:
    converter: ConverterStateDTO = field(default_factory=ConverterStateDTO)
    command: CommandContextDTO = field(default_factory=CommandContextDTO)
    window_sizes: dict[str, WindowSizeDTO] = field(default_factory=dict)


@dataclass(frozen=True)
class NumericWorkbenchPreferencesDTO:
    formatters: dict[str, FormattingOutputDTO] = field(default_factory=_default_formatter_preferences)
    log_preferences: CommandLogPreferencesDTO = field(default_factory=CommandLogPreferencesDTO)
    default_copy_field: str = "hexLE"
    key_panel_visible: bool = True
    auto_convert_enabled: bool = False


@dataclass(frozen=True)
class WorkspaceStateDTO:
    context: ApplicationContextDTO = field(default_factory=ApplicationContextDTO)
