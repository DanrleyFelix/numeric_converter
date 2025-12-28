class ValidationError(Exception):
    message: str

    def __init__(self, message: str, position: int | None = None):
        super().__init__(message)
        self.message = message
        self.position = position


class InvalidStartError(ValidationError):
    pass


class InvalidOperatorSequenceError(ValidationError):
    pass


class ParenthesisMismatchError(ValidationError):
    pass


class UnknownTokenError(ValidationError):
    pass


class UnknownVariableError(ValidationError):
    pass
