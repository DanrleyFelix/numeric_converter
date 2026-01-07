import json
from pathlib import Path
from src.application.dto.formatting_context import FormattingOutputDTO

DEFAULT_FORMATTER: dict[str, FormattingOutputDTO] = {
    "decimal": FormattingOutputDTO(4, True),
    "binary": FormattingOutputDTO(4, True),
    "hexBE": FormattingOutputDTO(2, True),
    "hexLE": FormattingOutputDTO(2, True)
}


class FormattingPreferencesRepository:
    def __init__(self, root: Path):
        self.file = root / "data" / "preferences_formatter.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, FormattingOutputDTO]:
        if not self.file.exists():
            return DEFAULT_FORMATTER
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                raw: dict = json.load(f)
        except json.JSONDecodeError:
            return DEFAULT_FORMATTER
        ctx: dict[str, FormattingOutputDTO] = raw.get("formatters", {})
        return {
            key: FormattingOutputDTO(
                group_size=ctx.get(key, {}).get("group_size", DEFAULT_FORMATTER[key].group_size),
                zero_pad=ctx.get(key, {}).get("zero_pad", DEFAULT_FORMATTER[key].zero_pad))
            for key in DEFAULT_FORMATTER}

    def save(self, context: dict[str, FormattingOutputDTO]):
        payload = {
            "formatters": {
                k: {"group_size": v.group_size, "zero_pad": v.zero_pad}
                for k, v in context.items()
            }
        }
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
