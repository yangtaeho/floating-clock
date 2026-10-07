"""Qt desktop regression checks, including real focus and popup selection."""
from dataclasses import replace
from datetime import datetime
from itertools import product
from pathlib import Path
import sys
import ctypes
from ctypes import wintypes
from unittest.mock import patch

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from clock_core import ClockPreferences, DATE_PRESETS, TIME_PRESETS, format_clock
from main import ClockApp


def verify_labels(app):
    QApplication.processEvents()
    for label in (app.time_label, app.date_label, app.status_label):
        if not label.isVisible():
            continue
        metrics = QFontMetrics(label.font())
        assert label.width() >= metrics.horizontalAdvance(label.text()), f"Clipped: {label.text()}"
        assert label.height() >= metrics.height(), "Text clipped vertically"
        assert label.mapTo(app.root, QPoint(0, 0)).y() + label.height() <= app.root.height() - 4


def verify_alpha(window):
    image = window.grab().toImage()
    assert image.pixelColor(0, 0).alpha() == 0, "Square corner is opaque"
    values = {image.pixelColor(x, y).alpha() for x in range(22) for y in range(22)}
    assert any(0 < alpha < 255 for alpha in values), "Rounded edge has no antialias alpha"


def native_topmost(app):
    user = ctypes.WinDLL("user32")
    function = user.GetWindowLongPtrW
    function.argtypes, function.restype = [wintypes.HWND, ctypes.c_int], ctypes.c_ssize_t
    return bool(function(int(app.root.winId()), -20) & 8)


def run(capture=False):
    qt = QApplication.instance() or QApplication([])
    qt.setFont(QFont("Malgun Gothic", 9))
    qt.setStyle("Fusion")
    qt.setQuitOnLastWindowClosed(False)
    with patch("main.load_settings", return_value={}), patch("main.save_settings") as save, \
            patch("main.ChimeAudio.play", return_value=True) as play:
        app = ClockApp()
        app.monitor.auto_hide_enabled = lambda: False
        qt.processEvents()
        assert app.preferences == ClockPreferences()
        assert app.height <= 80
        assert not app.header_label.isVisible() and not app.status_label.isVisible()
        assert app.date_label.text() == format_clock(datetime.now().astimezone()).date
        print("Checking Qt display combinations...", flush=True)
        combinations = 0
        for size, theme, hour, seconds, time_preset, date_preset in product(
                ("compact", "large"), ("light", "dark"), (12, 24), (True, False), TIME_PRESETS, DATE_PRESETS):
            app.update_preferences(ClockPreferences(size, theme, hour, seconds, time_preset, date_preset))
            verify_labels(app)
            verify_alpha(app.root)
            assert app.header_label.isVisible() == (size == "large")
            combinations += 1
        app.restore_defaults()
        print(f"Checked {combinations} combinations; checking focus and dropdowns...", flush=True)
        app.root.activateWindow()
        app.root.setFocus()
        QTest.qWait(100)
        QTest.keyClick(app.root, Qt.Key_Comma, Qt.ControlModifier)
        qt.processEvents()
        assert app.settings_panel is not None, "Ctrl+, did not open settings"
        panel = app.settings_panel
        QTest.qWait(100)
        assert qt.activeWindow() is panel
        for name, value in (("hour_cycle", 24), ("show_seconds", False), ("theme", "dark"),
                            ("size", "large"), ("hourly_chime", False)):
            control = panel.controls[name][1]
            QTest.mouseClick(control, Qt.LeftButton)
            qt.processEvents()
            assert getattr(app.preferences, name) == value
            assert qt.activeWindow() is panel, f"Setting {name} stole activation"
            assert qt.focusWidget() is control, f"Setting {name} stole focus"
            assert panel.controls[name][1] is control, "Control was rebuilt"
        assert save.call_args.args[0]["hourly_chime"] is False
        assert panel.geometry().bottom() <= panel.screen().availableGeometry().bottom()
        plays = play.call_count
        QTest.mouseClick(panel.chime_preview_button, Qt.LeftButton)
        qt.processEvents()
        assert play.call_count == plays + 1
        assert not app.preferences.hourly_chime, "Preview changed chime preference"
        assert qt.activeWindow() is panel and qt.focusWidget() is panel.chime_preview_button
        for name in ("time_preset", "date_preset", "mode"):
            combo = panel.controls[name]
            combo.setFocus()
            initial = combo.currentIndex()
            QTest.mouseClick(combo, Qt.LeftButton, pos=QPoint(combo.width() - 12, combo.height() // 2))
            qt.processEvents()
            assert combo.view().isVisible(), f"{name} dropdown did not open"
            QTest.qWait(1100)  # Clock and Shell timers while the popup is open.
            assert combo.view().isVisible(), f"Timer closed {name} dropdown"
            QTest.keyClick(combo.view(), Qt.Key_Down)
            QTest.keyClick(combo.view(), Qt.Key_Return)
            QTest.qWait(50)
            assert combo.currentIndex() != initial, f"{name} selection failed"
            assert getattr(app.preferences, name) == combo.currentData()
            assert qt.activeWindow() is panel, f"{name} stole activation"
            assert qt.focusWidget() is combo, f"{name} lost focus"
        for mode, expected in (("always", True), ("never", False)):
            combo = panel.controls["mode"]
            combo.setFocus()
            app.set_preference("mode", mode)
            qt.processEvents()
            QTest.qWait(1100)  # Let native popup cleanup and policy repair finish.
            assert qt.activeWindow() is panel and qt.focusWidget() is combo
            if sys.platform == "win32":
                assert native_topmost(app) == expected, f"Native topmost for {mode}: {native_topmost(app)}"
        assert save.call_args.args[0]["schema_version"] == 3
        QTest.keyClick(panel, Qt.Key_Comma, Qt.ControlModifier)
        qt.processEvents()
        assert app.settings_panel is None
        app.restore_defaults()
        app.popup(QPoint(100, 100))
        qt.processEvents()
        menu = app.popup_menu
        QTest.keyClick(menu, Qt.Key_Down)
        QTest.keyClick(menu, Qt.Key_Return)
        qt.processEvents()
        assert app.popup_menu is None and app.preferences.size == "large"
        app.popup(QPoint(100, 100))
        qt.processEvents()
        QTest.keyClick(app.popup_menu, Qt.Key_Escape)
        qt.processEvents()
        assert app.popup_menu is None
        if capture:
            folder = Path("previews")
            folder.mkdir(exist_ok=True)
            for size, theme in product(("compact", "large"), ("light", "dark")):
                app.update_preferences(replace(ClockPreferences(), size=size, theme=theme))
                qt.processEvents()
                app.root.grab().save(str(folder / f"{size}-{theme}.png"))
                app.toggle_settings()
                qt.processEvents()
                app.settings_panel.grab().save(str(folder / f"settings-{theme}.png"))
                verify_alpha(app.settings_panel)
                app.toggle_settings()
                app.popup(QPoint(100, 300))
                qt.processEvents()
                app.popup_menu.grab().save(str(folder / f"menu-{theme}.png"))
                app.dismiss_popup()
            app.restore_defaults()
            qt.processEvents()
            app.root.grab().save("preview.png")
        first = app.time_label.text()
        QTest.qWait(1300)
        assert app.time_label.text() != first
        app.popup(QPoint(100, 100))
        app.close()
        qt.processEvents()
        assert app.closing
        print(f"PASS: {combinations} Qt combinations, per-pixel antialiasing, stable focus during "
              "settings and live dropdown selection, no-activate topmost, shortcuts, popup, timer and exit")


if __name__ == "__main__":
    run(capture="--capture" in sys.argv)
