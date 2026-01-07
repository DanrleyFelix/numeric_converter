class EvaluationError(Exception):
    pass


class DivisionByZeroError(EvaluationError):
    pass


class InvalidUnaryOperationError(EvaluationError):
    pass