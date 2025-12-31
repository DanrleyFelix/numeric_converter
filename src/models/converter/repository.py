import json
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONTEXT = {
    "decimal": {"group_size": 3, "zero_pad": False},  # ex: 100 121 100
    "binary": {"group_size": 4, "zero_pad": True},    # ex: 0001 1011 0011
    "hexBE": {"group_size": 2, "zero_pad": True},     # ex: 0E 00 FF
    "hexLE": {"group_size": 2, "zero_pad": True},     # ex: FF 00 ...
}


class PreferencesManager:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.preferences_file = self.root / "data" / "preferences.json"
        self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
        self._preferences: Dict[str, Any] = self._load_preferences()

    def _load_preferences(self) -> Dict[str, Any]:
        if self.preferences_file.exists():
            try:
                with open(self.preferences_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_preferences(self):
        with open(self.preferences_file, "w", encoding="utf-8") as f:
            json.dump(self._preferences, f, indent=4)

    def set_preference(self, key: str, value: Any):
        self._preferences[key] = value
        self.save_preferences()

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self._preferences.get(key, default)

    def get_context(self) -> Dict[str, Any]:
        use_default = self._preferences.get("default", True)
        if use_default:
            return DEFAULT_CONTEXT
        return self._preferences.get("context", DEFAULT_CONTEXT)
