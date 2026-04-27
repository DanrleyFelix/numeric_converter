from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceRow:
    key: object
    values: tuple[str, ...]
