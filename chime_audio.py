"""Qt sound adapter; the schedule and waveform stay independent of the UI."""
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect


class ChimeAudio:
    def __init__(self, parent):
        self.path = Path(__file__).resolve().parent / "assets" / "hourly-chime.wav"
        self.effect = QSoundEffect(parent)
        self.effect.setLoopCount(1)
        self.effect.setVolume(0.5)
        self.effect.setSource(QUrl.fromLocalFile(str(self.path)))

    def play(self):
        # Do not queue a signal for later if a device/source is unavailable.
        if self.effect.status() == QSoundEffect.Status.Ready:
            self.effect.play()
            return True
        return False

    def stop(self):
        self.effect.stop()
