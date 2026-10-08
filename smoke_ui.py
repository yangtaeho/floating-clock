"""Qt desktop regression checks, including real focus and popup selection."""
from dataclasses import replace
from datetime import datetime
from itertools import product
from pathlib import Path
import sys
import ctypes
from ctypes import wintypes
from unittest.mock import patch

from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QFont, QFontMetrics, QEnterEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from clock_core import ClockPreferences, DATE_PRESETS, TIME_PRESETS, format_clock
from main import ClockApp
from app_metadata import VERSION, ASSETS
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon


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
    qt.setWindowIcon(QIcon(str(ASSETS / "icon.png")))
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
                ("compact", "large"), ("light", "dark", "aurora"), (12, 24), (True, False), TIME_PRESETS, DATE_PRESETS):
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
            panel.scroll.ensureWidgetVisible(combo)
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
            panel.scroll.ensureWidgetVisible(combo)
            combo.setFocus()
            app.set_preference("mode", mode)
            qt.processEvents()
            QTest.qWait(1100)  # Let native popup cleanup and policy repair finish.
            assert qt.activeWindow() is panel and qt.focusWidget() is combo
            if sys.platform == "win32":
                assert native_topmost(app) == expected, f"Native topmost for {mode}: {native_topmost(app)}, preference={app.preferences.mode}, cached={app.topmost}"
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
        # Information access from F1, repeated calls, settings and context menu.
        app.root.activateWindow()
        app.root.setFocus()
        QTest.qWait(100)
        QTest.keyClick(app.root, Qt.Key_F1)
        qt.processEvents()
        about = app.about_panel
        assert about and about.isVisible() and VERSION in about.version_label.text()
        assert not about.windowIcon().isNull()
        app.show_about()
        assert app.about_panel is about, "Duplicate information window"
        QTest.keyClick(about.close_button, Qt.Key_F1)
        qt.processEvents()
        assert app.about_panel is about
        QTest.qWait(1100)
        assert qt.activeWindow() is about and qt.focusWidget() is about.close_button
        for theme in ("light", "dark"):
            app.set_preference("theme", theme)
            qt.processEvents()
            assert app.about_panel is about and about.colors == app.colors
            verify_alpha(about)
            assert about.version_label.width() >= QFontMetrics(about.version_label.font()).horizontalAdvance(about.version_label.text())
            assert about.geometry().bottom() <= about.screen().availableGeometry().bottom()
            if capture:
                Path("previews").mkdir(exist_ok=True)
                about.grab().save(f"previews/about-{theme}.png")
        QTest.keyClick(about.close_button, Qt.Key_Escape)
        qt.processEvents()
        assert app.about_panel is None and not app.closing
        app.toggle_settings()
        QTest.qWait(100)
        QTest.keyClick(app.settings_panel.controls["size"][0], Qt.Key_F1)
        qt.processEvents()
        assert app.about_panel and app.settings_panel
        app.about_panel.close()
        app.settings_panel.close()
        app.popup(QPoint(100, 100))
        qt.processEvents()
        app.popup_menu.buttons[-2].click()
        qt.processEvents()
        assert app.about_panel and app.popup_menu is None
        app.about_panel.close()
        if app.tray:
            assert app.tray.icon.isVisible() and app.root.windowType() == Qt.Tool
            if sys.platform == "win32":
                user = ctypes.WinDLL("user32")
                style = user.GetWindowLongW(int(app.root.winId()), -20)
                assert style & 0x80 and not style & 0x40000, "Taskbar app window style"
            app.tray.visibility.trigger()
            qt.processEvents()
            assert not app.root.isVisible() and app.poll_timer.isActive()
            first = app.time_label.text()
            QTest.qWait(1300)
            assert not app.root.isVisible() and app.time_label.text() != first
            app.tray.activate(QSystemTrayIcon.Trigger)
            qt.processEvents()
            assert app.root.isVisible()
            app.tray.settings.trigger()
            qt.processEvents()
            assert app.settings_panel
            panel = app.settings_panel
            app.tray.settings.trigger()
            assert app.settings_panel is panel
            app.settings_panel.close()
            app.tray.about.trigger()
            qt.processEvents()
            assert app.about_panel
            app.about_panel.close()
        # A desktop without a tray must retain a reachable regular window.
        with patch("main.TrayAdapter.available", return_value=False):
            fallback = ClockApp()
            qt.processEvents()
            assert fallback.tray is None and fallback.root.windowType() == Qt.Window
            assert fallback.root.isVisible()
            fallback.shutdown()
        if capture:
            folder = Path("previews")
            folder.mkdir(exist_ok=True)
            for size, theme in product(("compact", "large"), ("light", "dark", "aurora")):
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
        # New recovery, content sizing and every exit confirmation route.
        app.settings_panel and app.settings_panel.close()
        app.about_panel and app.about_panel.close()
        app.restore_defaults()
        app.set_preference('hour_cycle', 24)
        app.set_preference('date_preset', 'slash')
        app.set_preference('show_seconds', False)
        narrow = app.root.width()
        app.set_preference('time_preset', 'korean')
        app.set_preference('show_seconds', True)
        assert app.root.width() > narrow, 'Formats did not change width'
        app.root.move(-10000, 10000)
        app.display_signature = None
        app.check_displays()
        bounds = app.root.screen().availableGeometry()
        assert bounds.contains(app.root.geometry()), 'Display recovery left clock outside'
        assert save.call_args.args[0]['x'] == app.root.x()
        app.set_preference('mode', 'never')
        if app.tray:
            QTest.mouseClick(app.hide_button, Qt.LeftButton)
            assert not app.root.isVisible() and app.tick_timer.isActive()
            app.tray.restore.trigger()
            qt.processEvents()
            assert app.root.isVisible() and not app.topmost
            app.hide_clock()
            if app.hotkey.registered:
                user = ctypes.WinDLL('user32')
                for key in (0x11, 0x12, 0x10, 0x43):
                    user.keybd_event(key, 0, 0, 0)
                for key in (0x43, 0x10, 0x12, 0x11):
                    user.keybd_event(key, 0, 2, 0)
                QTest.qWait(150)
                assert not app.root.isVisible(), 'First step must not restore'
                user.keybd_event(0x43, 0, 0, 0)
                user.keybd_event(0x43, 0, 2, 0)
                QTest.qWait(150)
                assert app.root.isVisible(), 'Native global sequence did not restore hidden clock'
            app.show_clock()
        # Configurable hotkey input suspends native and app shortcuts.
        app.toggle_settings()
        panel = app.settings_panel
        panel.scroll.ensureWidgetVisible(panel.shortcut_editor)
        panel.shortcut_editor.setFocus()
        qt.processEvents()
        assert not app.hotkey.registered and app.hotkey.suspended
        panel.shortcut_editor.setKeySequence('Ctrl+Alt+F10')
        QTest.mouseClick(panel.shortcut_apply, Qt.LeftButton)
        qt.processEvents()
        assert app.preferences.recovery_shortcut == 'Ctrl+Alt+F10'
        assert app.hotkey.registered and save.call_args.args[0]['recovery_shortcut'] == 'Ctrl+Alt+F10'
        QTest.mouseClick(panel.shortcut_disable, Qt.LeftButton)
        qt.processEvents()
        assert app.preferences.recovery_shortcut == '' and not app.hotkey.registered
        app.restore_defaults()
        panel.close()
        # Tooltip is immediate, above the icon, themed and does not steal focus.
        from time import perf_counter
        from PySide6.QtGui import QCursor
        for theme in ('light', 'dark'):
            app.set_preference('theme', theme)
            app.root.move(200, 250)
            app.root.activateWindow()
            app.root.setFocus()
            QTest.qWait(50)
            control = app.help_button if app.help_button.isVisible() else app.hide_button
            QCursor.setPos(app.root.mapToGlobal(QPoint(8,40)))
            QTest.mouseMove(app.root, QPoint(8,40))
            QTest.qWait(30)
            began = perf_counter()
            QCursor.setPos(control.mapToGlobal(QPoint(12, 12)))
            QTest.mouseMove(app.help_button if app.help_button.isVisible() else app.hide_button, QPoint(12, 12))
            # QTest's synthetic move can omit Enter after a native popup closes.
            # Send that Qt event explicitly; rendering and cursor-exit remain real.
            qt.sendEvent(control, QEnterEvent(QPointF(12,12),
                QPointF(control.mapTo(app.root, QPoint(12,12))),
                QPointF(control.mapToGlobal(QPoint(12,12)))))
            QTest.qWait(20)
            qt.processEvents()
            control = app.help_button if app.help_button.isVisible() else app.hide_button
            hint = control.hint
            assert hint and hint.isVisible(), (theme, control.isVisible(), control.underMouse(),
                QCursor.pos(), control.mapToGlobal(QPoint(12,12)), qt.widgetAt(QCursor.pos()))
            assert (perf_counter()-began)*1000 < 125
            assert hint.geometry().bottom() < control.mapToGlobal(QPoint(0,0)).y()
            assert qt.activeWindow() is app.root
            assert hint.colors == app.colors
            if capture:
                hint.grab().save(f'previews/tooltip-{theme}.png')
            QCursor.setPos(app.root.mapToGlobal(QPoint(8, 40)))
            QTest.mouseMove(app.root, QPoint(8, 40))
            QTest.qWait(40)
            qt.processEvents()
            assert control.hint is None
        # Closed and opened dark selectors use a dark palette including popup frame.
        app.toggle_settings()
        panel=app.settings_panel
        from PySide6.QtGui import QPalette
        for name in ('time_preset','date_preset','mode'):
            combo=panel.controls[name]
            panel.scroll.ensureWidgetVisible(combo)
            combo.showPopup()
            qt.processEvents()
            assert combo.view().viewport().palette().color(QPalette.Base).lightness() < 100
            assert combo.view().window().palette().color(QPalette.Window).lightness() < 100
            if capture:
                combo.view().window().grab().save(f'previews/selector-{name}-dark.png')
            combo.hidePopup()
        panel.close()
        # Actual mouse presses outside popup must clear its lifetime reference.
        app.popup(app.root.mapToGlobal(QPoint(app.root.width()+30, 0)))
        qt.processEvents()
        QTest.mouseClick(app.root, Qt.LeftButton, pos=QPoint(12, 35))
        qt.processEvents()
        assert app.popup_menu is None
        from PySide6.QtWidgets import QWidget, QMessageBox
        outside = QWidget()
        outside.show()
        app.popup(QPoint(100, 100))
        qt.processEvents()
        QTest.mouseClick(outside, Qt.LeftButton)
        qt.processEvents()
        assert app.popup_menu is None
        outside.close()
        for invoke in (app.close_button.click, app.root.close, app.close, app.escape,
                       app.tray.quit.trigger if app.tray else app.close):
            invoke()
            qt.processEvents()
            dialog = app.exit_dialog
            assert dialog and dialog.isVisible() and not app.closing
            app.close()
            assert app.exit_dialog is dialog, 'Repeated exit created duplicate dialog'
            assert dialog.defaultButton().text() == '취소'
            QTest.mouseClick(dialog.defaultButton(), Qt.LeftButton)
            qt.processEvents()
            assert app.exit_dialog is None and app.poll_timer.isActive() and not app.closing
        app.root.activateWindow()
        QTest.qWait(100)
        QTest.keyClick(app.root, Qt.Key_Q, Qt.ControlModifier)
        qt.processEvents()
        assert app.exit_dialog
        if capture:
            app.exit_dialog.grab().save('previews/exit-confirmation.png')
        app.exit_dialog.reject()
        qt.processEvents()
        app.show_about()
        assert 'https://github.com/yangtaeho/floating-clock' in app.about_panel.github_link.text()
        app.about_panel.close()
        app.restore_defaults()
        first = app.time_label.text()
        QTest.qWait(1300)
        assert app.time_label.text() != first
        app.popup(QPoint(100, 100))
        if app.tray:
            app.tray.quit.trigger()
        else:
            app.close()
        qt.processEvents()
        assert app.exit_dialog and not app.closing
        dialog = app.exit_dialog
        next(b for b in dialog.buttons() if dialog.buttonRole(b) == QMessageBox.AcceptRole).click()
        qt.processEvents()
        assert app.closing
        assert app.tray is None or not app.tray.icon.isVisible()
        print(f"PASS: {combinations} Qt combinations, per-pixel antialiasing, stable focus during "
              "settings and live dropdown selection, no-activate topmost, shortcuts, F1/about, tray visibility/actions/fallback, popup, timer and exit")


if __name__ == "__main__":
    run(capture="--capture" in sys.argv)
