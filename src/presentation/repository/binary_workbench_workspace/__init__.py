__all__ = ["BinaryWorkbenchWorkspaceRepository"]


def __getattr__(name: str):
    if name != "BinaryWorkbenchWorkspaceRepository":
        raise AttributeError(name)
    from src.presentation.repository.binary_workbench_workspace.repository import (
        BinaryWorkbenchWorkspaceRepository,
    )

    return BinaryWorkbenchWorkspaceRepository
