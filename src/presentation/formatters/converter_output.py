from src.application.dto.formatting_context import FormattingOutputDTO


class OutputFormatter:

    @staticmethod
    def _group_string(value: str, group_size: int) -> str:
        if group_size <= 0:
            return value
        first_group_len = len(value) % group_size or group_size
        groups = [value[:first_group_len]]
        for i in range(first_group_len, len(value), group_size):
            groups.append(value[i:i + group_size])
        return " ".join(groups)

    def format_decimal(self, value: int, formatter: FormattingOutputDTO) -> str:
        s = str(value)
        if formatter.zero_pad and formatter.group_size > 0:
            pad_len = (formatter.group_size - len(s) % formatter.group_size) % formatter.group_size
            s = "0" * pad_len + s
        return self._group_string(s, formatter.group_size)

    def format_binary(self, value: str, formatter: FormattingOutputDTO) -> str:
        s = value
        if formatter.group_size > 0 and formatter.zero_pad:
            pad_len = (formatter.group_size - len(s) % formatter.group_size) % formatter.group_size
            s = "0" * pad_len + s
        return self._group_string(s, formatter.group_size)

    def format_hex(self, value: bytes, formatter: FormattingOutputDTO) -> str:
        s = "".join(f"{b:02X}" for b in value)
        if formatter.group_size > 0 and formatter.zero_pad:
            pad_len = (formatter.group_size - len(s) % formatter.group_size) % formatter.group_size
            s = "0" * pad_len + s
        return self._group_string(s, formatter.group_size)
