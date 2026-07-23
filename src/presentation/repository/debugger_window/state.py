from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebuggerWindowState:
    """Persist one debugger window layout independently for each workspace."""

    x: int | None = None
    y: int | None = None
    width: int = 0
    height: int = 0
    maximized: bool = False
    horizontal_sizes: tuple[int, ...] = ()
    vertical_sizes: tuple[int, ...] = ()
    bottom_tab: int = 0

    def payload(self) -> dict[str, object]:
        """Return a JSON-compatible representation of this window state."""

        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "maximized": self.maximized,
            "horizontal_sizes": list(self.horizontal_sizes),
            "vertical_sizes": list(self.vertical_sizes),
            "bottom_tab": self.bottom_tab,
        }

