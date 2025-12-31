import json
from pathlib import Path
import pytest # type: ignore
from src.models.converter.repository import PreferencesManager, DEFAULT_CONTEXT 

ROOT_PATH = Path(__file__).parent.parent.parent

@pytest.mark.skip(reason="File access")
def test_preferences_manager_real():
    manager = PreferencesManager(root=ROOT_PATH)

    manager.set_preference("default", True)
    ctx = manager.get_context()
    assert ctx == DEFAULT_CONTEXT

    custom_context = {
        "decimal": {"group_size": 4, "zero_pad": True},
        "binary": {"group_size": 8, "zero_pad": True},
        "hexBE": {"group_size": 2, "zero_pad": False},
        "hexLE": {"group_size": 2, "zero_pad": False},
    }
    manager.set_preference("default", False)
    manager.set_preference("context", custom_context)

    manager2 = PreferencesManager(root=ROOT_PATH)
    ctx2 = manager2.get_context()
    print(ctx2)
    assert ctx2 == custom_context

    prefs_file = ROOT_PATH / "data" / "preferences.json"
    assert prefs_file.exists()

    with open(prefs_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["default"] is False
        assert data["context"] == custom_context

    manager2.set_preference("some_key", 123)
    manager3 = PreferencesManager(root=ROOT_PATH)
    assert manager3.get_preference("some_key") == 123
