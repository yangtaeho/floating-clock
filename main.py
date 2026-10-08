"""Portable Qt clock; pure clock logic and native Shell access stay separate."""
from dataclasses import replace
from datetime import datetime, timedelta
import sys
from time import monotonic

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics, QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox

from clock_core import ClockPreferences, TopmostMode, format_clock, next_tick_ms, should_be_topmost, ScreenArea, visible_position
from platform_adapter import TaskbarMonitor, WindowChrome, RecoveryHotkey, set_app_identity, app_identity
from settings import load_preferences, load_settings, save_settings
from ui_components import THEMES, RoundedWindow, ContextPopup, IconButton
from settings_panel import SettingsPanel
from chime_core import HourlyChime
from chime_audio import ChimeAudio
from app_metadata import APP_NAME, VERSION, AUTHOR, ASSETS, BUNDLE_ID
from about_panel import AboutPanel
from tray_adapter import TrayAdapter
from instance_adapter import InstanceGate


class ClockWindow(RoundedWindow):
    def __init__(self, controller):
        super().__init__(flags=controller.utility_flags)
        self.controller = controller
        self.setWindowTitle(APP_NAME)

    def contextMenuEvent(self, event):
        self.controller.popup(event.globalPos())

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.controller.clamp_position()
        self.controller.persist()

    def closeEvent(self, event):
        if self.controller.closing:
            event.accept()
        else:
            event.ignore()
            self.controller.close()


class ClockApp:
    def __init__(self):
        self.shell_identity = set_app_identity(BUNDLE_ID)
        QApplication.instance().setApplicationDisplayName(APP_NAME)
        self.monitor, self.chrome = TaskbarMonitor(), WindowChrome()
        saved = load_settings()
        self.preferences = load_preferences(saved)
        self.colors = THEMES[self.preferences.theme]
        self.topmost = None
        self.auto_hide = None
        self.closing = False
        self.save_error = False
        self.status = ""
        self.popup_menu = None
        self.settings_panel = None
        self.about_panel = None
        self.exit_dialog = None
        self.display_signature = None
        self.watched_screens = set()
        self.tray_available = TrayAdapter.available()
        self.utility_flags = (Qt.Tool if self.tray_available else Qt.Window) | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        self.tray = None
        QApplication.instance().setQuitOnLastWindowClosed(not self.tray_available)
        self.root = ClockWindow(self)
        self.chime = HourlyChime()
        self.chime_audio = ChimeAudio(self.root)
        layout = QVBoxLayout(self.root)
        self.layout = layout
        layout.setSpacing(1)
        self.header = QHBoxLayout()
        self.header_label = QLabel("LOCAL TIME")
        self.header_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.header.addWidget(self.header_label)
        self.header.addStretch()
        self.settings_button = IconButton('settings', '설정 (Ctrl+,)', self.toggle_settings, self.root)
        self.help_button = IconButton('help', '프로그램 정보와 사용법 (F1)', self.show_about, self.root)
        self.hide_button = IconButton('hide', '트레이로 숨기기', self.hide_clock, self.root)
        self.hide_button.setEnabled(self.tray_available)
        if not self.tray_available:
            self.hide_button.setToolTip('이 환경에서는 시스템 트레이를 사용할 수 없습니다')
        self.close_button = IconButton('close', '프로그램 종료 (Ctrl+Q)', self.close, self.root)
        self.icon_buttons = [self.settings_button, self.help_button, self.hide_button, self.close_button]
        self.header.setSpacing(2)
        layout.addLayout(self.header)
        self.time_label = QLabel()
        self.date_label = QLabel()
        self.status_label = QLabel()
        for label in (self.header_label, self.time_label, self.date_label, self.status_label):
            label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.time_label)
        layout.addWidget(self.date_label)
        layout.addWidget(self.status_label)
        self.shortcuts = []
        for key, callback in (("Ctrl+,", self.toggle_settings), ("Ctrl+Shift+S", self.toggle_settings),
                              ("Meta+,", self.toggle_settings), ("F1", self.show_about), ("Escape", self.escape), ("Ctrl+Q", self.close)):
            shortcut = QShortcut(QKeySequence(key), self.root)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.render_clock()
        self.reset_position(save=False)
        x, y = saved.get("x"), saved.get("y")
        if type(x) is int and type(y) is int:
            self.root.move(x, y)
            self.clamp_position()
        self.root.show()
        if self.tray_available:
            self.tray = TrayAdapter(self)
        application = QApplication.instance()
        self.hotkey = RecoveryHotkey(application, self.show_clock, self.preferences.recovery_shortcut)
        application.screenAdded.connect(self.schedule_display_recovery)
        application.screenRemoved.connect(self.schedule_display_recovery)
        self.check_displays()
        self.tick_timer = QTimer(self.root)
        self.tick_timer.setSingleShot(True)
        self.tick_timer.timeout.connect(self.tick)
        self.poll_timer = QTimer(self.root)
        self.poll_timer.timeout.connect(self.poll_taskbar)
        self.poll_timer.start(1000)
        self.tick()
        self.poll_taskbar()

    def render_clock(self):
        """Update existing labels and layout; never show/activate/recreate windows."""
        compact = self.preferences.size == "compact"
        self.colors = THEMES[self.preferences.theme]
        colors = self.colors
        self.root.radius = 12 if compact else 18
        self.root.apply_colors(colors)
        self.header_label.setVisible(not compact)
        self.settings_button.setVisible(not compact)
        self.help_button.setVisible(not compact)
        self.status_label.setVisible(not compact)
        # Only large mode uses the header; compact actions live in a side margin.
        for control in self.icon_buttons:
            self.header.removeWidget(control)
        if not compact:
            for control in self.icon_buttons:
                self.header.addWidget(control)
        self.layout.setContentsMargins(12 if compact else 20, 6 if compact else 14,
                                       60 if compact else 20, 7 if compact else 15)
        time_font = QFont("Malgun Gothic", 12 if compact else 30, QFont.Bold)
        date_font = QFont("Malgun Gothic", 8 if compact else 10)
        self.time_label.setFont(time_font)
        self.date_label.setFont(date_font)
        self.date_label.setStyleSheet(f"color: {colors['muted']};")
        self.status_label.setFont(QFont("Malgun Gothic", 8))
        self.status_label.setStyleSheet(f"color: {colors['accent']}; padding-top: 5px;")
        self.header_label.setStyleSheet(f"color: {colors['accent']};")
        for control in self.icon_buttons:
            control.update()
        samples = [format_clock(datetime(2088, 12, 20, hour, 58, 58) + timedelta(days=day), self.preferences)
                   for hour in range(24) for day in range(7)]
        metrics, date_metrics = QFontMetrics(time_font), QFontMetrics(date_font)
        content_width = max(max(metrics.horizontalAdvance(s.time), date_metrics.horizontalAdvance(s.date)) for s in samples)
        self.render_time()
        self.layout.invalidate()
        self.layout.activate()
        left, top, right, bottom = self.layout.getContentsMargins()
        width = content_width + left + right + 2
        if not compact:
            width = max(width, self.header.sizeHint().width() + left + right,
                        QFontMetrics(self.status_label.font()).horizontalAdvance('자동 · 자동 숨김 켜짐 / 항상 위') + left + right)
        height = max(56 if compact else 0, self.layout.sizeHint().height())
        self.root.setFixedSize(width, height)
        self.width, self.height = width, height
        if compact:
            self.hide_button.move(width - 57, 5)
            self.close_button.move(width - 30, 5)
        for control in (self.hide_button, self.close_button):
            control.show()
            control.raise_()
        self.clamp_position()

    def render_time(self):
        now = datetime.now().astimezone()
        clock = format_clock(now, self.preferences)
        self.time_label.setText(clock.time)
        self.date_label.setText(clock.date)
        return now

    def tick(self):
        now = self.render_time()
        if self.chime.poll(now, monotonic(), self.preferences.hourly_chime):
            self.chime_audio.play()
        if self.settings_panel:
            self.settings_panel.update_preview(now)
        self.tick_timer.start(next_tick_ms(now))

    def poll_taskbar(self):
        self.check_displays()
        result = self.monitor.auto_hide_enabled()
        if result is not None or not self.monitor.supported:
            self.auto_hide = result
        self.apply_policy()

    def apply_topmost(self, window, desired):
        if self.chrome.supported and window.windowHandle():
            # Keep Qt's native stacking policy in sync with the OS flag; owned
            # combo popups can otherwise undo SetWindowPos during WM processing.
            window.windowHandle().setFlag(Qt.WindowStaysOnTopHint, desired)
        result = self.chrome.set_topmost(int(window.winId()), desired)
        if result is None:  # Portable fallback, used only on a policy change.
            visible = window.isVisible()
            window.setAttribute(Qt.WA_ShowWithoutActivating)
            window.setWindowFlag(Qt.WindowStaysOnTopHint, desired)
            if visible:
                window.show()
            window.setAttribute(Qt.WA_ShowWithoutActivating, False)
        elif not result:
            self.status = "항상 위 표시를 적용할 수 없습니다"
            return False
        return True

    def apply_policy(self):
        mode = TopmostMode(self.preferences.mode)
        desired = should_be_topmost(mode, self.auto_hide)
        actual = self.chrome.is_topmost(int(self.root.winId()))
        # Closing a native popup can change the owner's z-order. Repair that
        # drift without activating either window, even if preferences match.
        if desired != self.topmost or (actual is not None and actual != desired):
            if self.apply_topmost(self.root, desired):
                self.topmost = desired
                if self.settings_panel:
                    self.apply_topmost(self.settings_panel, desired)
                if self.about_panel:
                    self.apply_topmost(self.about_panel, desired)
        if mode == TopmostMode.AUTO:
            if not self.monitor.supported:
                self.status = "자동 연동은 Windows 전용 · 일반 표시"
            elif self.auto_hide is None:
                self.status = "자동 · 작업 표시줄 상태 확인 중"
            else:
                self.status = "자동 · 자동 숨김 켜짐 / 항상 위" if desired else "자동 · 자동 숨김 꺼짐 / 일반 표시"
        else:
            self.status = "항상 위 표시" if desired else "일반 표시"
        if self.save_error:
            self.status = "설정 저장 실패 · 현재 실행은 계속됩니다"
        self.status_label.setText(self.status)
        if self.settings_panel:
            self.settings_panel.status_label.setText(self.status)
            self.settings_panel.update_hotkey_status()

    def update_preferences(self, preferences):
        if preferences.recovery_shortcut != self.preferences.recovery_shortcut:
            self.hotkey.configure(preferences.recovery_shortcut)
        if preferences.hourly_chime != self.preferences.hourly_chime:
            self.chime.reset()
            if not preferences.hourly_chime:
                self.chime_audio.stop()
        self.preferences = preferences
        self.render_clock()
        self.apply_policy()
        self.persist()
        if self.settings_panel:
            self.settings_panel.refresh()
        if self.about_panel:
            self.about_panel.refresh()

    def set_preference(self, name, value):
        self.update_preferences(replace(self.preferences, **{name: value}))

    def restore_defaults(self):
        self.update_preferences(ClockPreferences())

    def preview_chime(self):
        played = self.chime_audio.play()
        if self.settings_panel:
            self.settings_panel.chime_hint.setText(
                "매 정각 짧게 두 번 · 시스템 음량 적용" if played
                else "소리 준비 중이거나 오디오 장치를 사용할 수 없습니다")

    def toggle_settings(self):
        self.dismiss_popup()
        if self.settings_panel:
            self.settings_panel.close()
        else:
            self.settings_panel = SettingsPanel(self)
            self.apply_topmost(self.settings_panel, bool(self.topmost))

    def show_about(self):
        self.dismiss_popup()
        if not self.about_panel:
            self.about_panel = AboutPanel(self)
            self.apply_topmost(self.about_panel, bool(self.topmost))
        self.about_panel.raise_()
        self.about_panel.activateWindow()
        self.about_panel.close_button.setFocus()

    def popup(self, position):
        self.dismiss_popup()
        self.popup_menu = ContextPopup(self, position)

    def dismiss_popup(self):
        if self.popup_menu:
            self.popup_menu.close()

    def escape(self):
        if self.popup_menu:
            self.dismiss_popup()
        elif self.about_panel:
            self.about_panel.close()
        elif self.settings_panel:
            self.settings_panel.close()
        else:
            self.close()

    def reset_position(self, save=True):
        bounds = QApplication.primaryScreen().availableGeometry()
        self.root.move(max(bounds.left(), bounds.right() - self.root.width() - 20),
                       max(bounds.top(), bounds.bottom() - self.root.height() - 16))
        if save:
            self.persist()

    def clamp_position(self, window=None):
        window = window or self.root
        screens = [ScreenArea(r.x(), r.y(), r.width(), r.height())
                   for screen in QApplication.screens() for r in [screen.availableGeometry()]]
        x, y = visible_position(window.x(), window.y(), window.width(), window.height(), screens)
        changed = (x, y) != (window.x(), window.y())
        if changed:
            window.move(x, y)
        return changed

    def schedule_display_recovery(self, *args):
        if not self.closing:
            QTimer.singleShot(100, self.check_displays)

    def check_displays(self):
        if self.closing:
            return
        screens = QApplication.screens()
        for screen in screens:
            if screen not in self.watched_screens:
                screen.availableGeometryChanged.connect(self.schedule_display_recovery)
                screen.geometryChanged.connect(self.schedule_display_recovery)
                screen.logicalDotsPerInchChanged.connect(self.schedule_display_recovery)
        self.watched_screens = set(screens)
        signature = tuple((s.name(), s.availableGeometry().getRect(), s.logicalDotsPerInch()) for s in screens)
        if signature != self.display_signature:
            self.display_signature = signature
            changed = self.clamp_position()
            self.render_clock()
            for panel in (self.settings_panel, self.about_panel, self.exit_dialog):
                if panel:
                    self.clamp_position(panel)
            self.dismiss_popup()
            if changed:
                self.persist()

    def show_clock(self):
        self.clamp_position()
        self.root.show()
        self.apply_policy()
        self.root.raise_()
        self.root.activateWindow()
        if self.tray:
            self.tray.update_menu()

    def hide_clock(self):
        if not self.tray_available:
            return
        self.dismiss_popup()
        for panel in (self.settings_panel, self.about_panel):
            if panel:
                panel.close()
        self.root.hide()
        if self.tray:
            self.tray.update_menu()

    def persist(self):
        try:
            save_settings({"schema_version": 3, **self.preferences.to_mapping(), "x": self.root.x(), "y": self.root.y()})
            self.save_error = False
        except OSError:
            self.save_error = True
        self.apply_policy()

    def shutdown(self):
        if self.closing:
            return
        self.closing = True
        self.tick_timer.stop()
        self.poll_timer.stop()
        self.chime_audio.stop()
        self.hotkey.close()
        application = QApplication.instance()
        application.screenAdded.disconnect(self.schedule_display_recovery)
        application.screenRemoved.disconnect(self.schedule_display_recovery)
        if self.tray:
            self.tray.close()
        if self.about_panel:
            self.about_panel.close()
        self.dismiss_popup()
        if self.settings_panel:
            self.settings_panel.close()
        self.persist()
        self.root.close()
        QApplication.instance().quit()

    def close(self):
        if self.closing:
            return
        self.dismiss_popup()
        if self.exit_dialog:
            self.exit_dialog.raise_()
            self.exit_dialog.activateWindow()
            return
        dialog = QMessageBox(self.root)
        self.exit_dialog = dialog
        dialog.setWindowTitle('Floating Clock 종료')
        dialog.setIcon(QMessageBox.Question)
        dialog.setText('Floating Clock을 종료할까요?')
        dialog.setInformativeText('종료하면 정각 시보도 멈춥니다. 시계를 숨기려면 트레이로 숨기기를 선택하세요.')
        quit_button = dialog.addButton('종료', QMessageBox.AcceptRole)
        cancel_button = dialog.addButton('취소', QMessageBox.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.finished.connect(lambda result: self.finish_exit(dialog, quit_button))
        dialog.open()
        self.clamp_position(dialog)
        dialog.raise_()
        dialog.activateWindow()

    def finish_exit(self, dialog, quit_button):
        confirmed = dialog.clickedButton() is quit_button
        self.exit_dialog = None
        dialog.deleteLater()
        if confirmed:
            self.shutdown()


if __name__ == "__main__":
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setApplicationVersion(VERSION)
    application.setOrganizationName(AUTHOR)
    application.setWindowIcon(QIcon(str(ASSETS / "icon.png")))
    application.setFont(QFont("Malgun Gothic", 9))
    application.setStyle("Fusion")
    gate = None
    if '--verify-build' not in sys.argv and '--verify-audio' not in sys.argv:
        gate = InstanceGate()
        if not gate.claim():
            if gate.notify():
                sys.exit(0)
            QMessageBox.warning(None, APP_NAME, '기존 시계에 연결할 수 없습니다. 잠시 후 다시 실행하세요.')
            sys.exit(1)
    app = ClockApp()
    if gate:
        gate.activate(app.show_clock)
        application.aboutToQuit.connect(gate.close)
    if "--verify-build" in sys.argv or "--verify-audio" in sys.argv:
        from pathlib import Path
        import json
        def verify_build():
            folder = Path("build")
            folder.mkdir(exist_ok=True)
            app.root.grab().save(str(folder / "packaged-preview.png"))
            app.show_about()
            application.processEvents()
            app.about_panel.grab().save(str(folder / "packaged-about.png"))
            report = {
                "app_identity": app_identity(), "display_name": application.applicationDisplayName(),
                "version": VERSION, "icon_loaded": not application.windowIcon().isNull(),
                "about_visible": app.about_panel.isVisible(), "about_version": app.about_panel.version_label.text(),
                "tray_available": app.tray_available,
                "tray_visible": bool(app.tray and app.tray.icon.isVisible()),
                "tool_window": app.root.windowType() == Qt.Tool,
                "preferences": app.preferences.to_mapping(), "width": app.root.width(),
                "height": app.root.height(), "visible": app.root.isVisible(),
                "time": app.time_label.text(), "date": app.date_label.text(),
                "chime_asset_exists": app.chime_audio.path.is_file(),
                "chime_audio_status": app.chime_audio.effect.status().name
            }
            def finish():
                (folder / "packaged-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                app.shutdown()
            if '--verify-audio' in sys.argv:
                states = []
                app.chime_audio.effect.playingChanged.connect(lambda: states.append(app.chime_audio.effect.isPlaying()))
                report['audio_play_requested'] = app.chime_audio.play()
                def finish_audio():
                    report['audio_started'] = True in states
                    report['audio_finished'] = bool(states and states[-1] is False)
                    finish()
                QTimer.singleShot(1000, finish_audio)
            else:
                finish()
        QTimer.singleShot(1500, verify_build)
    sys.exit(application.exec())
