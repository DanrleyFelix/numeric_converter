from typing import List

from src.core.constants import (
    ERROR_INVALID_EXPRESSION,
    UNARY_OPERATORS,
    ARITHMETIC_OPERATORS,
    ASSIGNMENT_OPERATOR,
    CONDITIONAL_OPERATORS,
    MULTI_CHAR_OPERATORS,
    TEXTUAL_OPERATORS,
    BASE_PREFIXES)
from src.core.command_window.tokenizer import (
    Tokenizer,
    TokenizerError,
    TokenType,
    Token)
from src.core.command_window.validator.errors import (
    InvalidStartError,
    InvalidOperatorSequenceError,
    ParenthesisMismatchError,
    ValidationError,
    UnknownTokenError,
    UnknownVariableError)
from src.core.command_window.context import cmd_window_context


class ValidationState:
    POTENTIALLY_INVALID = 0
    ACCEPTABLE = 1
    is_error = False


class ExpressionValidator:

    @staticmethod
    def validate(expr: str) -> ValidationState:
        if not expr.strip():
            return ValidationState.POTENTIALLY_INVALID
        if _PartialExpressionAnalyzer(expr).is_partial():
            return ValidationState.POTENTIALLY_INVALID
        tokens = _Tokenizer(expr).tokenize()
        tokens = [t for t in tokens if t.type != TokenType.EOF]
        return _ExpressionChecker(tokens).check()


class _PartialExpressionAnalyzer:

    def __init__(self, expr: str):
        self.expr = expr

    def is_partial(self) -> bool:
        stripped = self.expr.rstrip()
        if not stripped:
            return True

        trailing = self._trailing_fragment(stripped)
        if not trailing:
            return False

        upper_fragment = trailing.upper()
        if trailing != "=" and any(
            op.startswith(trailing) and op != trailing
            for op in MULTI_CHAR_OPERATORS
        ):
            return True
        if self._could_be_textual_operator(stripped, trailing):
            return True
        if trailing.lower() in BASE_PREFIXES:
            return True
        if len(trailing) > 1 and any(
            prefix.startswith(trailing.lower()) and prefix != trailing.lower()
            for prefix in BASE_PREFIXES
        ):
            return True
        return False

    def _trailing_fragment(self, text: str) -> str:
        end = len(text)
        start = end
        operator_chars = set("+-*/%<>=!&|^~")

        while start > 0:
            char = text[start - 1]
            if char.isspace() or char in "()" or char in operator_chars:
                break
            start -= 1

        return text[start:end]

    def _could_be_textual_operator(self, text: str, trailing: str) -> bool:
        upper_fragment = trailing.upper()
        candidates = [
            alias
            for alias in TEXTUAL_OPERATORS
            if alias.startswith(upper_fragment)
        ]
        if not candidates:
            return False

        fragment_start = len(text) - len(trailing)
        prefix = text[:fragment_start]
        try:
            prefix_tokens = [
                token
                for token in Tokenizer(prefix).tokenize()
                if token.type != TokenType.EOF
            ]
        except TokenizerError:
            return False
        if not self._prefix_is_structurally_valid(prefix_tokens):
            return False

        previous = prefix_tokens[-1] if prefix_tokens else None
        for alias in candidates:
            if alias == "NOT":
                if (
                    (previous is None or previous.type in {
                        TokenType.OPERATOR,
                        TokenType.LPAREN,
                    })
                    and self._is_unary_textual_delimited(text, fragment_start, trailing)
                ):
                    return True
            elif (
                previous is not None
                and previous.type in {
                    TokenType.NUMBER,
                    TokenType.IDENTIFIER,
                    TokenType.RPAREN,
                }
                and self._is_binary_textual_delimited(text, fragment_start)
            ):
                return True
        return False

    def _is_unary_textual_delimited(
        self,
        text: str,
        fragment_start: int,
        trailing: str,
    ) -> bool:
        before = self._character_before(text, fragment_start)
        after = self._character_after(text, fragment_start, trailing)
        operator_chars = set("+-*/%<>=!&|^~")
        left_delimited = (
            before is None
            or before.isspace()
            or before == "("
            or before in operator_chars
        )
        right_delimited = after is None or after.isspace() or after == "("
        return left_delimited and right_delimited

    def _is_binary_textual_delimited(self, text: str, fragment_start: int) -> bool:
        before = self._character_before(text, fragment_start)
        left_delimited = before is not None and (before.isspace() or before == ")")
        return left_delimited

    def _character_before(self, text: str, position: int) -> str | None:
        if position <= 0:
            return None
        return text[position - 1]

    def _character_after(
        self,
        text: str,
        fragment_start: int,
        trailing: str,
    ) -> str | None:
        position = fragment_start + len(trailing)
        if position >= len(text):
            return None
        return text[position]

    def _prefix_is_structurally_valid(self, tokens: list[Token]) -> bool:
        if not tokens:
            return True
        try:
            _StructureValidator(tokens).validate()
            _SequenceValidator(tokens).validate()
        except ValidationError:
            return False
        return True


class _Tokenizer:

    def __init__(self, expr: str):
        self.expr = expr

    def tokenize(self) -> List[Token]:
        try:
            return Tokenizer(self.expr).tokenize()
        except TokenizerError as e:
            raise UnknownTokenError(ERROR_INVALID_EXPRESSION) from e
        

class _ExpressionChecker:

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens

    def check(self) -> ValidationState:
        return (_StructureValidator(self.tokens).validate() &
            _SequenceValidator(self.tokens).validate() &
            _SemanticValidator(self.tokens).validate())


class _StructureValidator:

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens

    def validate(self) -> ValidationState:
        return (self._check_start() &
            self._check_parentheses() &
            self._check_partial())

    def _check_start(self) -> ValidationState:
        first = self.tokens[0]
        if first.type == TokenType.OPERATOR and first.raw not in UNARY_OPERATORS:
            raise InvalidStartError(ERROR_INVALID_EXPRESSION, position=first.position)
        return ValidationState.ACCEPTABLE

    def _check_parentheses(self) -> ValidationState:
        balance = self._parentheses_balance_or_fail()
        return (ValidationState.POTENTIALLY_INVALID if balance > 0 else ValidationState.ACCEPTABLE)

    def _parentheses_balance_or_fail(self) -> int:
        balance = 0
        for t in self.tokens:
            if t.type == TokenType.LPAREN:
                balance += 1
            elif t.type == TokenType.RPAREN:
                balance -= 1
                if balance < 0:
                    raise ParenthesisMismatchError(
                        ERROR_INVALID_EXPRESSION,
                        position=t.position)
        return balance

    def _check_partial(self) -> ValidationState:
        return (ValidationState.POTENTIALLY_INVALID if self._is_incomplete_syntax() else ValidationState.ACCEPTABLE)
    
    def _is_incomplete_syntax(self) -> bool:
        return (not self.tokens or self._ends_with_open_construct())
    
    def _ends_with_open_construct(self) -> bool:
        dangling_tokens = {TokenType.OPERATOR, TokenType.LPAREN}
        return self.tokens[-1].type in dangling_tokens


class _SequenceValidator:

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens

    def validate(self) -> ValidationState:
        for i in range(len(self.tokens) - 1):
            self._validate_pair(i)
        return ValidationState.ACCEPTABLE

    def _validate_pair(self, i: int) -> None:
        prev = self.tokens[i]
        curr = self.tokens[i + 1]
        if self._operator_before_rparen(prev, curr): self._invalid(curr)
        if self._empty_parentheses(prev, curr): self._paren_error(curr)
        if self._implicit_multiplication(prev, curr): self._invalid(curr)
        if self._invalid_operator_sequence(i): self._invalid(curr)

    def _operator_before_rparen(self, prev: Token, curr: Token) -> bool:
        return (prev.type == TokenType.OPERATOR and curr.type == TokenType.RPAREN)

    def _empty_parentheses(self, prev: Token, curr: Token) -> bool:
        return (prev.type == TokenType.LPAREN and curr.type == TokenType.RPAREN)

    def _implicit_multiplication(self, prev: Token, curr: Token) -> bool:
        left_tokens = {TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.RPAREN}
        right_tokens = {TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.LPAREN}
        return prev.type in left_tokens and curr.type in right_tokens

    def _invalid_operator_sequence(self, i: int) -> bool:
        prev = self.tokens[i]
        curr = self.tokens[i + 1]

        if not self._both_operators(prev, curr): return False
        if self._binary_after_binary(curr): return True
        if self._unary_after_unary(prev, curr): return True
        if self._invalid_signed_unary(prev, curr): return True
        if self._unary_without_operand(i): return True
        return False

    def _both_operators(self, prev: Token, curr: Token) -> bool:
        return (prev.type == TokenType.OPERATOR and curr.type == TokenType.OPERATOR)

    def _binary_after_binary(self, curr: Token) -> bool:
        return curr.raw not in UNARY_OPERATORS

    def _unary_after_unary(self, prev: Token, curr: Token) -> bool:
        return (prev.raw in UNARY_OPERATORS and curr.raw in UNARY_OPERATORS)

    def _invalid_signed_unary(self, prev: Token, curr: Token) -> bool:
        if curr.raw not in {"+", "-"}:
            return False
        return prev.raw not in (ARITHMETIC_OPERATORS | ASSIGNMENT_OPERATOR | CONDITIONAL_OPERATORS)

    def _unary_without_operand(self, i: int) -> bool:
        if i + 2 >= len(self.tokens):
            return True
        return self.tokens[i + 2].type not in {
            TokenType.NUMBER,
            TokenType.IDENTIFIER,
            TokenType.LPAREN}

    def _invalid(self, token: Token) -> None:
        raise InvalidOperatorSequenceError(
            ERROR_INVALID_EXPRESSION,
            position=token.position)

    def _paren_error(self, token: Token) -> None:
        raise ParenthesisMismatchError(
            ERROR_INVALID_EXPRESSION,
            position=token.position)


class _SemanticValidator:

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens

    def validate(self) -> ValidationState:
        return (self._check_variables() & self._check_assignments())

    def _check_variables(self) -> ValidationState:
        for i, t in enumerate(self.tokens):
            if t.type != TokenType.IDENTIFIER:
                continue
            if not self._is_lhs(i) and cmd_window_context.get_variable(t.raw) is None:
                raise UnknownVariableError(
                    f'Unknown variable "{t.raw}".',
                    position=t.position,
                )
        return ValidationState.ACCEPTABLE

    def _is_lhs(self, i: int) -> bool:
        return (
            i + 1 < len(self.tokens)
            and self.tokens[i + 1].type == TokenType.OPERATOR
            and self.tokens[i + 1].raw == "="
        )

    def _check_assignments(self) -> ValidationState:
        assignment_operators = [i for i, t in enumerate(self.tokens) if t.type == TokenType.OPERATOR and t.raw == "="]
        is_simple_assignment = (
            len(assignment_operators) == 1
            and assignment_operators[0] == 1
            and self.tokens[0].type == TokenType.IDENTIFIER
        )
        if assignment_operators and not is_simple_assignment:
            raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION)
        return ValidationState.ACCEPTABLE




