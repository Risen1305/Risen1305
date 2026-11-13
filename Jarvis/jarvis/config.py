import tomllib
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "config.toml"
DATA_DIR = Path.home() / ".jarvis"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    for section in ("user", "location", "weather", "voice", "ears", "clap", "brain", "apps"):
        cfg.setdefault(section, {})
    DATA_DIR.mkdir(exist_ok=True)
    return cfg
