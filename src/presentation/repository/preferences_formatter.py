import json
from pathlib import Path

from src.core.binary_workbench.selection_limits import (
    DEFAULT_SELECTION_LIMIT_BYTES,
    normalized_selection_limit,
)
from src.modules.application_dtos import NumericWorkbenchPreferencesDTO
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_BYTE_GROUP_OPTIONS,
    BINARY_WORKBENCH_DEFAULT_BLOCK_SIZE,
    BINARY_WORKBENCH_DEFAULT_CACHE_MAX_BLOCKS,
)
from src.modules.binary_workbench_dtos import (
    BinaryWorkbenchEditRulesDTO,
    BinaryWorkbenchPreferencesDTO,
)
from src.modules.command_window_dtos import CommandLogPreferencesDTO
from src.modules.converter_dtos import FormattingOutputDTO

DEFAULT_FORMATTER: dict[str, FormattingOutputDTO] = {
    "decimal": FormattingOutputDTO(3, False),
    "binary": FormattingOutputDTO(4, True),
    "hexBE": FormattingOutputDTO(2, True),
    "hexLE": FormattingOutputDTO(2, True)
}


class FormattingPreferencesRepository:
    def __init__(self, root: Path):
        self.file = root / "data" / "numeric_workbench" / "preferences.json"
        self._legacy_file = root / "data" / "preferences_formatter.json"
        self._legacy_context_file = root / "data" / "contexts" / "default_context.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, FormattingOutputDTO]:
        return self.load_preferences().formatters

    def load_preferences(self) -> NumericWorkbenchPreferencesDTO:
        raw = self._read_preferences_payload()
        if raw is None:
            return NumericWorkbenchPreferencesDTO(formatters=DEFAULT_FORMATTER)
        ctx_raw = raw.get("formatters", {})
        ctx: dict[str, dict] = ctx_raw if isinstance(ctx_raw, dict) else {}
        return NumericWorkbenchPreferencesDTO(
            formatters={
                key: FormattingOutputDTO(
                    group_size=ctx.get(key, {}).get("group_size", DEFAULT_FORMATTER[key].group_size),
                    zero_pad=ctx.get(key, {}).get("zero_pad", DEFAULT_FORMATTER[key].zero_pad))
                for key in DEFAULT_FORMATTER
            },
            log_preferences=self._log_preferences(raw.get("logs", {})),
            key_panel_visible=raw.get("key_panel_visible", True),
            auto_convert_enabled=raw.get("auto_convert_enabled", False),
        )

    def _read_preferences_payload(self) -> dict | None:
        if self.file.exists():
            return self._read_json(self.file)
        legacy = self._read_json(self._legacy_file)
        if legacy is None:
            legacy = {}
        legacy_context = self._read_json(self._legacy_context_file)
        if legacy_context:
            legacy = {
                **legacy,
                "key_panel_visible": legacy_context.get("key_panel_visible", True),
                "auto_convert_enabled": legacy_context.get("auto_convert_enabled", False),
            }
        return legacy or None

    def _read_json(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw: dict = json.load(f)
        except json.JSONDecodeError:
            return None
        return raw if isinstance(raw, dict) else None

    def save(self, context: dict[str, FormattingOutputDTO]):
        preferences = self.load_preferences()
        self.save_preferences(
            NumericWorkbenchPreferencesDTO(
                formatters=context,
                log_preferences=preferences.log_preferences,
                key_panel_visible=preferences.key_panel_visible,
                auto_convert_enabled=preferences.auto_convert_enabled,
            )
        )

    def save_preferences(self, preferences: NumericWorkbenchPreferencesDTO):
        payload = {
            "formatters": {
                k: {"group_size": v.group_size, "zero_pad": v.zero_pad}
                for k, v in preferences.formatters.items()
            },
            "logs": {
                "enabled": preferences.log_preferences.enabled,
                "assignment_only": preferences.log_preferences.assignment_only,
                "single_unary_only": preferences.log_preferences.single_unary_only,
                "no_operator": preferences.log_preferences.no_operator,
                "assignment_operator": preferences.log_preferences.assignment_operator,
                "binary_operator_only": preferences.log_preferences.binary_operator_only,
            },
            "key_panel_visible": preferences.key_panel_visible,
            "auto_convert_enabled": preferences.auto_convert_enabled,
        }
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

    def _log_preferences(self, raw: object) -> CommandLogPreferencesDTO:
        values = raw if isinstance(raw, dict) else {}
        return CommandLogPreferencesDTO(
            enabled=self._bool(values.get("enabled"), True),
            assignment_only=self._bool(values.get("assignment_only"), True),
            single_unary_only=self._bool(values.get("single_unary_only"), True),
            no_operator=self._bool(values.get("no_operator"), True),
            assignment_operator=self._bool(values.get("assignment_operator"), True),
            binary_operator_only=self._bool(values.get("binary_operator_only"), False),
        )

    def _bool(self, raw: object, default: bool) -> bool:
        return raw if isinstance(raw, bool) else default


class BinaryWorkbenchPreferencesRepository:
    def __init__(self, root: Path):
        self.file = root / "data" / "binary_workbench" / "preferences.json"
        self._legacy_context_file = root / "data" / "contexts" / "default_context.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> BinaryWorkbenchPreferencesDTO:
        raw = self._read_json(self.file)
        if raw is None:
            raw = self._legacy_payload()
        return BinaryWorkbenchPreferencesDTO(
            group_bytes=self._group_bytes(raw.get("group_bytes") if raw else None),
            uppercase_bytes=self._bool(raw.get("uppercase_bytes") if raw else None, True),
            uppercase_instructions=self._bool(raw.get("uppercase_instructions") if raw else None, True),
            block_size=self._positive_int(
                raw.get("block_size") if raw else None,
                BINARY_WORKBENCH_DEFAULT_BLOCK_SIZE,
            ),
            cache_max_blocks=self._positive_int(
                raw.get("cache_max_blocks") if raw else None,
                BINARY_WORKBENCH_DEFAULT_CACHE_MAX_BLOCKS,
            ),
            selection_limit_bytes=normalized_selection_limit(
                self._positive_int(
                    raw.get("selection_limit_bytes") if raw else None,
                    DEFAULT_SELECTION_LIMIT_BYTES,
                )
            ),
            binary_edit_rules=self._edit_rules(
                raw.get("binary_edit_rules") if raw else None,
                BinaryWorkbenchEditRulesDTO(),
            ),
            assembly_edit_rules=self._edit_rules(
                raw.get("assembly_edit_rules") if raw else None,
                BinaryWorkbenchEditRulesDTO(allow_byte_shift=True),
            ),
        )

    def save(self, preferences: BinaryWorkbenchPreferencesDTO) -> None:
        payload = {
            "group_bytes": preferences.group_bytes,
            "uppercase_bytes": preferences.uppercase_bytes,
            "uppercase_instructions": preferences.uppercase_instructions,
            "block_size": preferences.block_size,
            "cache_max_blocks": preferences.cache_max_blocks,
            "selection_limit_bytes": preferences.selection_limit_bytes,
            "binary_edit_rules": self._edit_rules_payload(preferences.binary_edit_rules),
            "assembly_edit_rules": self._edit_rules_payload(preferences.assembly_edit_rules),
        }
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

    def _legacy_payload(self) -> dict | None:
        legacy = self._read_json(self._legacy_context_file)
        if not legacy:
            return None
        binary = legacy.get("binary_workbench", {})
        raw_tabs = binary.get("tabs", []) if isinstance(binary, dict) else []
        tabs = raw_tabs if isinstance(raw_tabs, list) else []
        first = tabs[0] if tabs and isinstance(tabs[0], dict) else {}
        view = first.get("view_preferences", {}) if isinstance(first, dict) else {}
        return {
            "group_bytes": view.get("group_bytes") if isinstance(view, dict) else None,
            "uppercase_bytes": view.get("uppercase_bytes") if isinstance(view, dict) else None,
            "uppercase_instructions": view.get("uppercase_instructions") if isinstance(view, dict) else None,
            "block_size": first.get("block_size") if isinstance(first, dict) else None,
            "cache_max_blocks": first.get("cache_max_blocks") if isinstance(first, dict) else None,
        }

    def _read_json(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw: dict = json.load(f)
        except json.JSONDecodeError:
            return None
        return raw if isinstance(raw, dict) else None

    def _group_bytes(self, raw: object) -> int:
        default = BINARY_WORKBENCH_BYTE_GROUP_OPTIONS[0]
        value = raw if isinstance(raw, int) else default
        return value if value in BINARY_WORKBENCH_BYTE_GROUP_OPTIONS else default

    def _bool(self, raw: object, default: bool) -> bool:
        return raw if isinstance(raw, bool) else default

    def _positive_int(self, raw: object, default: int) -> int:
        value = raw if isinstance(raw, int) else default
        return value if value > 0 else default

    def _edit_rules(
        self,
        raw: object,
        default: BinaryWorkbenchEditRulesDTO,
    ) -> BinaryWorkbenchEditRulesDTO:
        values = raw if isinstance(raw, dict) else {}
        byte_shift = self._bool(
            values.get("allow_byte_shift"),
            self._bool(values.get("allow_insert_shift"), default.allow_byte_shift)
            or self._bool(values.get("allow_remove_shift"), default.allow_byte_shift),
        )
        editor_edit = self._bool(
            values.get("allow_editor_edit"),
            self._bool(values.get("allow_bytes_edit"), default.allow_editor_edit)
            and self._bool(values.get("allow_assembly_edit"), default.allow_editor_edit),
        )
        return BinaryWorkbenchEditRulesDTO(
            allow_byte_shift=byte_shift,
            allow_editor_edit=editor_edit,
            allow_free_edit_after_original_end=self._bool(
                values.get("allow_free_edit_after_original_end"),
                self._bool(values.get("allow_append_offsets"), default.allow_free_edit_after_original_end),
            ),
        )

    def _edit_rules_payload(self, rules: BinaryWorkbenchEditRulesDTO) -> dict[str, bool]:
        return {
            "allow_byte_shift": rules.allow_byte_shift,
            "allow_editor_edit": rules.allow_editor_edit,
            "allow_free_edit_after_original_end": rules.allow_free_edit_after_original_end,
        }
