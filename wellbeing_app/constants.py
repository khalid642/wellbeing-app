import os
from pathlib import Path

APP_ID = "com.github.amanah.wellbeing"
APP_NAME = "Wellbeing App"

XDG_CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
XDG_CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
XDG_STATE_HOME = os.environ.get('XDG_STATE_HOME', os.path.expanduser('~/.local/state'))

CONFIG_DIR = Path(XDG_CONFIG_HOME) / "wellbeing-app"
CACHE_DIR = Path(XDG_CACHE_HOME) / "wellbeing-app"
LOGS_DIR = Path(XDG_STATE_HOME) / "wellbeing-app"
DB_PATH = CONFIG_DIR / "wellbeing.db"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
