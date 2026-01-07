from src.application.contracts.preferences_contract import IFormattingPreferencesRepository
from src.application.dto import FormattingOutputDTO


class FormattingPreferencesService:
    def __init__(self, repo: IFormattingPreferencesRepository):
        self.repo = repo

    def get_format(self) -> dict[str, FormattingOutputDTO]:
        return self.repo.load()

    def update(self, key: str, ctx: FormattingOutputDTO):
        current = self.repo.load()
        current[key] = ctx
        self.repo.save(current)
