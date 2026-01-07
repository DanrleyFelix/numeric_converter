import json
from pathlib import Path
import pytest # type: ignore
from src.presentation.repository.preferences_formatter import (
    FormattingPreferencesRepository,
    DEFAULT_FORMATTER)
from src.application.dto.formatting_context import FormattingOutputDTO


ROOT_PATH = Path(__file__).parent.parent.parent
print(ROOT_PATH)


def test_load_with_invalid_json_falls_back_to_default(tmp_path: Path):
    repo = FormattingPreferencesRepository(tmp_path)
    repo.file.write_text("{ invalid json", encoding="utf-8")
    result = repo.load()
    assert result == DEFAULT_FORMATTER


def test_save_and_load_roundtrip(tmp_path):
    repo = FormattingPreferencesRepository(tmp_path)
    context = {
        "decimal": FormattingOutputDTO(3, False),
        "binary": FormattingOutputDTO(8, True),
        "hexBE": FormattingOutputDTO(2, False),
        "hexLE": FormattingOutputDTO(4, True)}

    repo.save(context)
    loaded = repo.load()

    assert loaded["decimal"].group_size == 3
    assert loaded["decimal"].zero_pad is False
    assert loaded["binary"].group_size == 8
    assert loaded["binary"].zero_pad is True

def test_load_returns_default_when_file_does_not_exist(tmp_path):
    repo = FormattingPreferencesRepository(tmp_path)
    result = repo.load()
    for key, default in DEFAULT_FORMATTER.items():
        assert result[key].group_size == default.group_size
        assert result[key].zero_pad == default.zero_pad

def test_load_without_formatters_key_uses_default(tmp_path: Path):
    repo = FormattingPreferencesRepository(tmp_path)
    repo.file.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    result = repo.load()
    assert result == DEFAULT_FORMATTER

def test_partial_formatter_configuration(tmp_path: Path):
    repo = FormattingPreferencesRepository(tmp_path)
    data = {
        "formatters": {
            "decimal": {
                "group_size": 10,
                "zero_pad": False
            }
        }
    }
    repo.file.write_text(json.dumps(data), encoding="utf-8")
    result = repo.load()
    assert result["decimal"].group_size == 10
    assert result["decimal"].zero_pad is False
    assert result["binary"] == DEFAULT_FORMATTER["binary"]

def test_missing_formatter_fields_fallback_individually(tmp_path: Path):
    repo = FormattingPreferencesRepository(tmp_path)
    data = {
        "formatters": {
            "hexBE": {
                "group_size": 6
            }
        }
    }
    repo.file.write_text(json.dumps(data), encoding="utf-8")
    result = repo.load()
    assert result["hexBE"].group_size == 6
    assert result["hexBE"].zero_pad == DEFAULT_FORMATTER["hexBE"].zero_pad

def test_load_always_returns_all_default_keys(tmp_path: Path):
    repo = FormattingPreferencesRepository(tmp_path)
    repo.save({
        "decimal": FormattingOutputDTO(1, True)
    })
    result = repo.load()
    assert set(result.keys()) == set(DEFAULT_FORMATTER.keys())

def test_save_creates_file_and_directories(tmp_path: Path):
    repo = FormattingPreferencesRepository(tmp_path)
    repo.save(DEFAULT_FORMATTER)
    assert repo.file.exists()
    assert repo.file.is_file()

