from dataclasses import dataclass


@dataclass(frozen=True)
class HelpPageDefinition:
    title: str
    subtitle: str
    html: str
