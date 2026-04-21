import re
from pathlib import Path

Tokens = dict[str, str]

VAR_RE = re.compile(r"\$(\w[\w\-]*)\s*:\s*(.+?);")
IMPORT_RE = re.compile(r'@import\s+"(.+?)";')

BASE_DIR = Path(__file__).resolve().parent.parent
STYLE_DIR = BASE_DIR / "design" / "style"


def load_tokens(path: Path) -> Tokens:
    text = path.read_text(encoding="utf-8")
    return {
        name: value.strip()
        for name, value in VAR_RE.findall(text)
    }


def apply_tokens(qss: str, tokens: Tokens) -> str:
    for name in sorted(tokens, key=len, reverse=True):
        qss = qss.replace(f"${name}", tokens[name])
    return qss


def expand_imports(qss: str, base_dir: Path) -> str:
    def replacer(match):
        path = base_dir / match.group(1)
        return path.read_text(encoding="utf-8")

    while IMPORT_RE.search(qss):
        qss = IMPORT_RE.sub(replacer, qss)

    return qss


def load_stylesheet(tokens_path: Path, qss_path: Path) -> str:
    tokens = load_tokens(tokens_path)

    qss = qss_path.read_text(encoding="utf-8")
    qss = expand_imports(qss, qss_path.parent)
    qss = apply_tokens(qss, tokens)

    return qss


STYLESHEET = load_stylesheet(
    STYLE_DIR / "tokens.qss",
    STYLE_DIR / "main.qss",
)
