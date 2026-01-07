from numbers import Number


class _Context:
    
    def __init__(self):
        self.__variables: dict[str, Number] = {"ANS": 0}
        self.__history: list[str] = []

    def set_variable(self, name: str, value: Number) -> None:
        self.__variables[name] = value

    def get_variable(self, name: str) -> Number | None:
        return self.__variables.get(name)
    
    def get_history(self) -> None:
        return self.__history

    def add_to_history(self, instruction: str) -> None:
        self.__history.append(instruction)

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


cmd_window_context = _Context()
