"""Portable Qt clock; pure clock logic and native Shell access stay separate."""
from dataclasses import replace
from datetime import datetime, timedelta
import sys
from time import monotonic

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout

from clock_core import ClockPreferences, TopmostMode, format_clock, next_tick_ms, should_be_topmost
from platform_adapter import TaskbarMonitor, WindowChrome
from settings import load_preferences, load_settings, save_settings
from ui_components import THEMES, RoundedWindow, ContextPopup, button
from settings_panel import SettingsPanel
from chime_core import HourlyChime
from chime_audio import ChimeAudio


class ClockWindow(RoundedWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Floating Clock")

    def contextMenuEvent(self, event):
        self.controller.popup(event.globalPos())

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.controller.persist()

    def closeEvent(self, event):
        self.controller.shutdown()
        event.accept()


class ClockApp:
    def __init__(self):
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
        self.settings_button = button("설정", self.toggle_settings, self.root)
        self.header.addWidget(self.settings_button)
        # Compact close button is laid out over the right margin, not a title row.
        self.close_button = button("×", self.close, self.root)
        self.close_button.setFixedSize(22, 22)
        self.close_button.setFont(QFont("Segoe UI", 12))
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
                              ("Meta+,", self.toggle_settings), ("Escape", self.escape), ("Ctrl+Q", self.close)):
            shortcut = QShortcut(QKeySequence(key), self.root)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.render_clock()
        self.reset_position(save=False)
        x, y = saved.get("x"), saved.get("y")
        if type(x) is int and type(y) is int:
            self.root.move(x, y)
            self.clamp_position()
        self.root.show()
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
        self.status_label.setVisible(not compact)
        self.layout.setContentsMargins(12 if compact else 20, 6 if compact else 14,
                                       30 if compact else 20, 7 if compact else 15)
        time_font = QFont("Malgun Gothic", 12 if compact else 30, QFont.Bold)
        date_font = QFont("Malgun Gothic", 8 if compact else 10)
        self.time_label.setFont(time_font)
        self.date_label.setFont(date_font)
        self.date_label.setStyleSheet(f"color: {colors['muted']};")
        self.status_label.setFont(QFont("Malgun Gothic", 8))
        self.status_label.setStyleSheet(f"color: {colors['accent']}; padding-top: 5px;")
        self.header_label.setStyleSheet(f"color: {colors['accent']};")
        self.close_button.setStyleSheet(f"color: {colors['subtle']}; padding: 0px;")
        samples = [format_clock(datetime(2088, 12, 20, hour, 58, 58) + timedelta(days=day), self.preferences)
                   for hour in range(24) for day in range(7)]
        metrics, date_metrics = QFontMetrics(time_font), QFontMetrics(date_font)
        content_width = max(max(metrics.horizontalAdvance(s.time), date_metrics.horizontalAdvance(s.date)) for s in samples)
        self.render_time()
        self.layout.invalidate()
        self.layout.activate()
        width = max(220 if compact else 340, content_width + (44 if compact else 42))
        height = max(56 if compact else 180, self.layout.sizeHint().height())
        self.root.setFixedSize(width, height)
        self.width, self.height = width, height
        self.close_button.move(width - 27, 5 if compact else 13)
        self.close_button.raise_()
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
        result = self.monitor.auto_hide_enabled()
        if result is not None or not self.monitor.supported:
            self.auto_hide = result
        self.apply_policy()

    def apply_topmost(self, window, desired):
        result = self.chrome.set_topmost(int(window.winId()), desired)
        if result is None:  # Portable fallback, used only on a policy change.
            window.setAttribute(Qt.WA_ShowWithoutActivating)
            window.setWindowFlag(Qt.WindowStaysOnTopHint, desired)
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

    def update_preferences(self, preferences):
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

    def popup(self, position):
        self.dismiss_popup()
        self.popup_menu = ContextPopup(self, position)

    def dismiss_popup(self):
        if self.popup_menu:
            self.popup_menu.close()

    def escape(self):
        if self.popup_menu:
            self.dismiss_popup()
        elif self.settings_panel:
            self.settings_panel.close()
        else:
            self.close()

    def reset_position(self, save=True):
        bounds = self.root.screen().availableGeometry()
        self.root.move(max(bounds.left(), bounds.right() - self.root.width() - 20),
                       max(bounds.top(), bounds.bottom() - self.root.height() - 16))
        if save:
            self.persist()

    def clamp_position(self):
        bounds = self.root.screen().availableGeometry()
        x = max(bounds.left(), min(self.root.x(), bounds.right() - self.root.width() + 1))
        y = max(bounds.top(), min(self.root.y(), bounds.bottom() - self.root.height() + 1))
        self.root.move(x, y)

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
        self.dismiss_popup()
        if self.settings_panel:
            self.settings_panel.close()
        self.persist()

    def close(self):
        self.root.close()


if __name__ == "__main__":
    application = QApplication(sys.argv)
    application.setFont(QFont("Malgun Gothic", 9))
    application.setStyle("Fusion")
    app = ClockApp()
    if "--verify-build" in sys.argv:
        from pathlib import Path
        import json
        def verify_build():
            folder = Path("build")
            folder.mkdir(exist_ok=True)
            app.root.grab().save(str(folder / "packaged-preview.png"))
            (folder / "packaged-verification.json").write_text(json.dumps({
                "preferences": app.preferences.to_mapping(), "width": app.root.width(),
                "height": app.root.height(), "visible": app.root.isVisible(),
                "time": app.time_label.text(), "date": app.date_label.text(),
                "chime_asset_exists": app.chime_audio.path.is_file(),
                "chime_audio_status": app.chime_audio.effect.status().name
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            app.close()
        QTimer.singleShot(1500, verify_build)
    sys.exit(application.exec())
