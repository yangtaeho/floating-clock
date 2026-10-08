"""Audible Qt smoke test: load and preview the original double beep once."""
from datetime import datetime, timedelta
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from main import ClockApp


def run():
    qt = QApplication([])
    with patch("main.load_settings", return_value={}), patch("main.save_settings"):
        app = ClockApp()
        app.monitor.auto_hide_enabled = lambda: False
        app.set_preference("hourly_chime", False)
        app.toggle_settings()
        panel = app.settings_panel
        for _ in range(50):
            if app.chime_audio.effect.status() == QSoundEffect.Status.Ready:
                break
            QTest.qWait(100)
        assert app.chime_audio.effect.status() == QSoundEffect.Status.Ready
        states = []
        app.chime_audio.effect.playingChanged.connect(
            lambda: states.append(app.chime_audio.effect.isPlaying()))
        QTest.mouseClick(panel.chime_preview_button, Qt.LeftButton)
        QTest.qWait(700)
        assert True in states and states[-1] is False, f"Playback did not finish: {states}"
        assert qt.activeWindow() is panel and qt.focusWidget() is panel.chime_preview_button
        assert not app.preferences.hourly_chime
        # Exercise timer-to-audio wiring without changing the OS clock or replaying audio.
        app.set_preference("hourly_chime", True)
        hour = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
        with patch.object(app, "render_time", return_value=hour - timedelta(seconds=1)), \
                patch("main.monotonic", return_value=1):
            app.tick()
        with patch.object(app, "render_time", return_value=hour), \
                patch("main.monotonic", return_value=2), patch.object(app.chime_audio, "play") as play:
            app.tick()
            app.tick()
            play.assert_called_once()
        app.shutdown()
        qt.processEvents()
        print("PASS: Qt audio Ready, preview started and finished, focus preserved, hourly timer played once")


if __name__ == "__main__":
    run()
