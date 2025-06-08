import json
import json
import os
from pathlib import Path

CONFIG_DIR = 'moltest'
CONFIG_FILE = 'config.json'

def _get_config_path() -> Path:
    base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    cfg_dir = base / CONFIG_DIR
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / CONFIG_FILE


def load_config() -> dict:
    path = _get_config_path()
    if path.is_file():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg: dict) -> None:
    path = _get_config_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4)
