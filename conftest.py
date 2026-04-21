import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def reset_command_window_context():
    from src.core.command_window.context import cmd_window_context

    cmd_window_context.clear_all()
    yield
    cmd_window_context.clear_all()
