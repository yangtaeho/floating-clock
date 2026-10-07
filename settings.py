import json
import os
import sys
from pathlib import Path
from clock_core import ClockPreferences, TopmostMode


def settings_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "FloatingClock" / "settings.json"


def load_settings() -> dict:
    try:
        value = json.loads(settings_path().read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {}
        return value
    except (OSError, ValueError):
        return {}


def load_mode(settings: dict) -> TopmostMode:
    try:
        return TopmostMode(settings.get("mode", "auto"))
    except (ValueError, TypeError):
        return TopmostMode.AUTO


def load_preferences(settings: dict) -> ClockPreferences:
    settings = dict(settings)
    version = settings.get("schema_version", 1)
    if (type(version) is not int or version < 3) and settings.get("date_preset") == "korean_full":
        settings["date_preset"] = "korean_spaced_short"
    return ClockPreferences.from_mapping(settings)


def save_settings(settings: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
