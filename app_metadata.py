"""Product identity shared by the UI and native distribution builders."""
from pathlib import Path

APP_NAME = "Floating Clock"
VERSION = "1.0.0"
AUTHOR = "yangtaeho"
BUNDLE_ID = "com.yangtaeho.floatingclock"
DESCRIPTION = "Offline desktop clock with an hourly chime"
ASSETS = Path(__file__).resolve().parent / "assets"
