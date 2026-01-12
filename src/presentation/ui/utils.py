from pathlib import Path


def load_all_qss(folder: Path) -> str:
    qss_text = ""
    for file in sorted(folder.glob("*.qss")):  # sorted para ordem previsível
        with open(file, "r", encoding="utf-8") as f:
            qss_text += f.read() + "\n"
    return qss_text

QSS_FOLDER = Path(r"src\presentation\ui\design\style")
STYLESHEET = load_all_qss(QSS_FOLDER)