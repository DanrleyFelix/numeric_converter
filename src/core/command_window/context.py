from numbers import Number


class _Context:
    
    def __init__(self):
        self.__variables: dict[str, Number] = {"ANS": 0}
        self.__history: list[str] = []

    def set_variable(self, name: str, value: Number) -> None:
        self.__variables[name] = value

    def get_variable(self, name: str) -> Number | None:
        return self.__variables.get(name)

    def get_variables(self) -> dict[str, Number]:
        return dict(self.__variables)

    def remove_variable(self, name: str) -> None:
        if name == "ANS":
            return
        self.__variables.pop(name, None)
    
    def get_history(self) -> list[str]:
        return list(self.__history)

    def add_to_history(self, instruction: str) -> None:
        self.__history.append(instruction)

    def set_history(self, instructions: list[str]) -> None:
        self.__history = list(instructions)

    def remove_history_line(self, index: int) -> None:
        if 0 <= index < len(self.__history):
            self.__history.pop(index)

    def clear_history(self) -> None:
        self.__history.clear()

    def clear_variables(self) -> None:
        self.__variables.clear()
        self.set_variable("ANS", 0)

    def clear_all(self) -> None:
        self.__history.clear()
        self.__variables.clear()
        self.set_variable("ANS", 0)

    def restore(self, variables: dict[str, Number], history: list[str]) -> None:
        self.__variables = dict(variables) if variables else {"ANS": 0}
        if "ANS" not in self.__variables:
            self.__variables["ANS"] = 0
        self.__history = list(history)



cmd_window_context = _Context()
