"""Qt surfaces: one antialiased boundary, shared theme, stable controls."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout

THEMES = {
    "light": {"bg": "#F8FAFC", "fg": "#172538", "muted": "#718094", "subtle": "#9AA7B7",
              "accent": "#137A70", "hover": "#E6F0EE", "border": "#E5EAF0", "panel": "#FFFFFF",
              "control": "#F0F3F7", "selected": "#E0F0EB"},
    "dark": {"bg": "#171F2E", "fg": "#ECF2FA", "muted": "#9AAAC0", "subtle": "#72839B",
             "accent": "#80D6C7", "hover": "#2A3749", "border": "#2A3547", "panel": "#202B3C",
             "control": "#202B3C", "selected": "#24463F"},
}


class RoundedWindow(QWidget):
    def __init__(self, parent=None, flags=None, radius=14):
        if flags is None:
            flags = Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        super().__init__(parent, flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.colors = THEMES["light"]
        self.radius = radius
        self.drag_offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(self.colors["border"]), 1.0))
        painter.setBrush(QColor(self.colors["bg"]))
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), self.radius, self.radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_offset = None
        super().mouseReleaseEvent(event)

    def apply_colors(self, colors):
        self.colors = colors
        self.setStyleSheet(f"""
            QLabel {{ color: {colors['fg']}; background: transparent; border: none; }}
            QPushButton {{ color: {colors['fg']}; background: transparent; border: none;
                           border-radius: 7px; padding: 5px 10px; }}
            QPushButton:hover {{ background: {colors['hover']}; }}
            QPushButton:focus {{ background: {colors['hover']}; }}
            QPushButton:checked {{ color: {colors['accent']}; background: {colors['selected']}; }}
        """)
        self.update()


def button(text, callback, parent=None):
    control = QPushButton(text, parent)
    control.setCursor(Qt.PointingHandCursor)
    control.setFocusPolicy(Qt.StrongFocus)
    control.clicked.connect(callback)
    return control


class ContextPopup(RoundedWindow):
    def __init__(self, app, position):
        super().__init__(app.root, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint, radius=12)
        self.app = app
        self.apply_colors(app.colors)
        self.setAttribute(Qt.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        preferences = app.preferences
        choices = [
            ("설정…                         Ctrl+,", app.toggle_settings),
            ("큰 시계로" if preferences.size == "compact" else "작은 시계로",
             lambda: app.set_preference("size", "large" if preferences.size == "compact" else "compact")),
            ("다크 테마로" if preferences.theme == "light" else "라이트 테마로",
             lambda: app.set_preference("theme", "dark" if preferences.theme == "light" else "light")),
            ("24시간제로" if preferences.hour_cycle == 12 else "12시간제로",
             lambda: app.set_preference("hour_cycle", 24 if preferences.hour_cycle == 12 else 12)),
            ("초 숨기기" if preferences.show_seconds else "초 표시",
             lambda: app.set_preference("show_seconds", not preferences.show_seconds)),
            ("위치 초기화", app.reset_position), ("종료                             Ctrl+Q", app.close),
        ]
        self.buttons = []
        for index, (text, callback) in enumerate(choices):
            control = button(text, lambda checked=False, action=callback: self.choose(action), self)
            control.setStyleSheet("text-align: left; padding: 7px 12px;")
            layout.addWidget(control)
            self.buttons.append(control)
            if index == 4:
                layout.addSpacing(6)
        self.index = 0
        self.adjustSize()
        bounds = app.root.screen().availableGeometry()
        x = min(max(bounds.left(), position.x()), max(bounds.left(), bounds.right() - self.width() + 1))
        y = min(max(bounds.top(), position.y()), max(bounds.top(), bounds.bottom() - self.height() + 1))
        self.move(x, y)
        self.shortcuts = []
        for key, callback in (("Up", lambda: self.navigate(-1)), ("Down", lambda: self.navigate(1)),
                              ("Return", self.activate), ("Escape", self.close)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.show()
        self.buttons[0].setFocus()

    def navigate(self, delta):
        self.index = (self.index + delta) % len(self.buttons)
        self.buttons[self.index].setFocus()

    def activate(self):
        self.buttons[self.index].click()

    def choose(self, action):
        self.close()
        action()

    def dismiss(self):
        self.close()

    def closeEvent(self, event):
        if self.app.popup_menu is self:
            self.app.popup_menu = None
        super().closeEvent(event)
