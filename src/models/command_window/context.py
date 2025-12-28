from typing import Union

Number = Union[int, float]

class Context:
    def __init__(self):
        self.__variables: dict[str, Number] = {"ANS": 0}
        self.__history: list[str] = []

    def set_variable(self, name: str, value: Number) -> None:
        self.__variables[name] = value

    def get_variable(self, name: str) -> Number | None:
        return self.__variables.get(name)

    def add_to_history(self, instruction: str) -> None:
        self.__history.append(instruction)

    def remove_history_line(self, index: int) -> None:
        if 0 <= index < len(self.__history):
            self.__history.pop(index)

    def clear_history(self) -> None:
        self.__history.clear()
