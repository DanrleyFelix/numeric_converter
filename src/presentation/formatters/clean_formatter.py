from typing import Optional


class CleanFormatter:

    @staticmethod
    def format(value: Optional[str]) -> str:
        if value is None:
            return "0"
        return value.replace(" ", "")
