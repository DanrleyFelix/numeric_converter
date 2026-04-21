from src.application.dto.formatting_context import FormattingOutputDTO


class OutputFormatter:

    @staticmethod
    def _group_string(value: str, group_size: int) -> str:
        if group_size <= 0:
            return value
        first_group_len = len(value) % group_size or group_size
        groups = [value[:first_group_len]]
        for index in range(first_group_len, len(value), group_size):
            groups.append(value[index:index + group_size])
        return " ".join(groups)

    @staticmethod
    def _pad_to_group(value: str, formatter: FormattingOutputDTO) -> str:
        if not value or not formatter.zero_pad or formatter.group_size <= 0:
            return value

        pad_len = (formatter.group_size - len(value) % formatter.group_size) % formatter.group_size
        return ("0" * pad_len) + value

    def prepare_decimal_input(
        self,
        value: str,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        formatter = formatter or FormattingOutputDTO()
        return self._pad_to_group(value, formatter)

    def prepare_binary_input(
        self,
        value: str,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        formatter = formatter or FormattingOutputDTO()
        return self._pad_to_group(value, formatter)

    def prepare_hex_input(
        self,
        value: str,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        formatter = formatter or FormattingOutputDTO()
        prepared = self._pad_to_group(value.upper(), formatter)
        if prepared and len(prepared) % 2 == 1:
            prepared = f"0{prepared}"
        return prepared

    def format_decimal(
        self,
        value: int,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        formatter = formatter or FormattingOutputDTO()
        prepared = self.prepare_decimal_input(str(value), formatter)
        return self._group_string(prepared, formatter.group_size)

    def format_decimal_input(
        self,
        value: str,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        formatter = formatter or FormattingOutputDTO()
        prepared = self.prepare_decimal_input(value, formatter)
        return self._group_string(prepared, formatter.group_size)

    def format_binary(
        self,
        value: str,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        formatter = formatter or FormattingOutputDTO()
        prepared = self.prepare_binary_input(value, formatter)
        return self._group_string(prepared, formatter.group_size)

    def format_hex_input(
        self,
        value: str,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        formatter = formatter or FormattingOutputDTO()
        prepared = self.prepare_hex_input(value, formatter)
        return self._group_string(prepared, formatter.group_size)

    def format_hex(
        self,
        value: bytes,
        formatter: FormattingOutputDTO | None = None,
    ) -> str:
        formatter = formatter or FormattingOutputDTO()
        prepared = self._pad_to_group("".join(f"{byte:02X}" for byte in value), formatter)
        return self._group_string(prepared, formatter.group_size)
