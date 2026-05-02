import json
from pathlib import Path
from typing import Any


class COLOR:
    INFO = "#466CC3"
    SUCCESS = "#6AE899"
    FAILED = "#ED4D4D"
    INCOMPLETE = "#FFC222"


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def normalize_json_path(path: Path, directory: Path) -> Path:
    normalized = path.with_suffix(".json") if path.suffix.lower() != ".json" else path
    if not normalized.is_absolute() or directory not in normalized.parents:
        normalized = directory / normalized.name
    return normalized


def normalize_string_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def normalize_string_map(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}
