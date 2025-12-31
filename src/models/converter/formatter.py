from typing import Dict, Optional
from src.models.converter.repository import PreferencesManager


class InputFormatter:

    @staticmethod
    def format(value: Optional[str]) -> str:
        if value is None:
            return "0"
        return value.replace(" ", "")


class OutputFormatter:
    def __init__(self, prefs_manager: PreferencesManager):
        self.prefs_manager = prefs_manager

    @staticmethod
    def _normalize_context(context: Dict[str, any]) -> Dict[str, any]:

        group_size = context.get("group_size", 0)
        zero_pad = context.get("zero_pad", False)
        if not isinstance(group_size, int) or group_size < 0:
            group_size = 0
        if not isinstance(zero_pad, bool):
            zero_pad = False
        return {"group_size": group_size, "zero_pad": zero_pad}

    @staticmethod
    def _group_string(value: str, group_size: int) -> str:
        if group_size <= 0:
            return value
        first_group_len = len(value) % group_size or group_size
        groups = [value[:first_group_len]]
        for i in range(first_group_len, len(value), group_size):
            groups.append(value[i:i+group_size])
        return " ".join(groups)

    def _get_context(self, value_type: str, context: Optional[Dict] = None) -> Dict[str, any]:
        if context is not None:
            return self._normalize_context(context)
        full_context = self.prefs_manager.get_context()
        ctx = full_context.get(value_type, full_context[value_type])
        return self._normalize_context(ctx)

    def format_decimal(self, value: int, context: Optional[Dict] = None) -> str:
        context = self._get_context("decimal", context)
        s = str(value)
        if context["zero_pad"] and context["group_size"] > 0:
            pad_len = (context["group_size"] - len(s) % context["group_size"]) % context["group_size"]
            s = "0" * pad_len + s
        return self._group_string(s, context["group_size"])

    def format_binary(self, value: str, context: Optional[Dict] = None) -> str:
        context = self._get_context("binary", context)
        s = value
        pad_len = 0 if context["group_size"] <= 0 else \
            (context["group_size"] - len(s) % context["group_size"]) % context["group_size"]
        if context["zero_pad"]:
            s = "0" * pad_len + s
        return self._group_string(s, context["group_size"])

    def format_hex(self, value: bytes, value_type: str = "hexBE", context: Optional[Dict] = None) -> str:
        context = self._get_context(value_type, context)
        s = "".join(f"{b:02X}" for b in value)
        pad_len = 0 if context["group_size"] <= 0 else \
            (context["group_size"] - len(s) % context["group_size"]) % context["group_size"]
        if context["zero_pad"]:
            s = "0" * pad_len + s
        return self._group_string(s, context["group_size"])

    def format(self, value_type: str, value, context: Optional[Dict] = None) -> str:
        if value_type == "decimal":
            return self.format_decimal(value, context)
        elif value_type == "binary":
            return self.format_binary(value, context)
        elif value_type in ("hexBE", "hexLE"):
            return self.format_hex(value, value_type, context)
        else:
            return str(value)
