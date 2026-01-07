from typing import Optional


class InputFormatter:

    @staticmethod
    def format(value: Optional[str]) -> str:
        if value is None:
            return "0"
        return value.replace(" ", "")
