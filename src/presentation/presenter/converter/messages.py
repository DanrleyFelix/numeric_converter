from src.core.converter import MAX_BYTE_LENGTH

from src.presentation.presenter.converter.constants import CONVERTER_TYPE


def build_validation_message(from_type: str) -> str:
    if from_type == CONVERTER_TYPE.DECIMAL:
        return f"Decimal accepts only digits and up to {MAX_BYTE_LENGTH} bytes."
    if from_type == CONVERTER_TYPE.BINARY:
        return f"Binary accepts only 0 and 1 and up to {MAX_BYTE_LENGTH * 8} bits."
    return f"Hex accepts up to {MAX_BYTE_LENGTH} bytes."
