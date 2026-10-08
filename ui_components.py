"""Qt surfaces: one antialiased boundary, shared theme, stable controls."""
from PySide6.QtCore import Qt, QRectF, QEvent, QPointF, QPoint, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QKeySequence, QShortcut, QPolygonF, QFont, QCursor, QLinearGradient
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication, QLabel

THEMES = {
    "light": {"bg": "#F8FAFC", "fg": "#172538", "muted": "#718094", "subtle": "#9AA7B7",
              "accent": "#137A70", "hover": "#E6F0EE", "border": "#E5EAF0", "panel": "#FFFFFF",
              "control": "#F0F3F7", "selected": "#E0F0EB"},
    "dark": {"bg": "#171F2E", "fg": "#ECF2FA", "muted": "#9AAAC0", "subtle": "#72839B",
             "accent": "#80D6C7", "hover": "#2A3749", "border": "#2A3547", "panel": "#202B3C",
             "control": "#202B3C", "selected": "#24463F"},
    "aurora": {"bg": "#19263F", "fg": "#EFF7FF", "muted": "#B0BDD7", "subtle": "#8299BE",
               "accent": "#98E8CF", "hover": "#304666", "border": "#52688B", "panel": "#20304B",
               "control": "#263B57", "selected": "#285D60", "gradient_top": "#203C58", "gradient_bottom": "#29233F"},
}


class RoundedWindow(QWidget):
    def __init__(self, parent=None, flags=None, radius=14):
        if flags is None:
            flags = Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        super().__init__(parent, flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
        self.colors = THEMES["light"]
        self.radius = radius
        self.drag_offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(self.colors["border"]), 1.0))
        if 'gradient_top' in self.colors:
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor(self.colors['gradient_top']))
            gradient.setColorAt(1, QColor(self.colors['gradient_bottom']))
            painter.setBrush(gradient)
        else:
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
        if self.colors == colors and self.styleSheet():
            return
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


class IconButton(QPushButton):
    """Consistent drawn icons, independent of symbol fonts and platform glyphs."""
    def __init__(self, kind, label, callback, parent):
        super().__init__(parent)
        self.kind = kind
        self.hint = None
        self.hint_timer = QTimer(self)
        self.hint_timer.setInterval(16)
        self.hint_timer.timeout.connect(self.check_hint_position)
        self.setFixedSize(24, 24)
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(callback)
        self.pressed.connect(self.dismiss_hint)

    def paintEvent(self, event):
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = self.window().colors
        if self.underMouse() or self.hasFocus():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(colors['hover']))
            painter.drawRoundedRect(QRectF(1, 1, self.width()-2, self.height()-2), 6, 6)
        painter.translate(self.width()/2, self.height()/2)
        painter.scale(self.width()/24, self.height()/24)
        painter.setPen(QPen(QColor(colors['muted'] if self.isEnabled() else colors['subtle']), 1.5,
                            Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        if self.kind == 'close':
            painter.drawLine(QPointF(-4,-4), QPointF(4,4))
            painter.drawLine(QPointF(-4,4), QPointF(4,-4))
        elif self.kind == 'hide':
            painter.drawLine(QPointF(-5,2), QPointF(5,2))
        elif self.kind == 'help':
            painter.drawEllipse(QRectF(-7,-7,14,14))
            painter.setFont(QFont('Segoe UI', 9, QFont.Bold))
            painter.drawText(QRectF(-7,-8,14,16), Qt.AlignCenter, '?')
        else:
            points = []
            for i in range(32):
                radius = 7 if i % 4 in (1,2) else 5.4
                angle = math.pi * 2 * i / 32
                points.append(QPointF(radius * math.cos(angle), radius * math.sin(angle)))
            painter.drawPolygon(QPolygonF(points))
            painter.drawEllipse(QRectF(-2.3,-2.3,4.6,4.6))

    def enterEvent(self, event):
        self.update()
        self.dismiss_hint()
        if self.isEnabled():
            self.hint = RoundedWindow(self, Qt.ToolTip | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint |
                                      Qt.WindowDoesNotAcceptFocus, radius=8)
            self.hint.setAttribute(Qt.WA_ShowWithoutActivating)
            self.hint.setAttribute(Qt.WA_DeleteOnClose)
            self.hint.apply_colors(self.window().colors)
            layout = QVBoxLayout(self.hint)
            layout.setContentsMargins(10, 6, 10, 6)
            label = QLabel(self.toolTip())
            layout.addWidget(label)
            self.hint.adjustSize()
            origin = self.mapToGlobal(QPoint(self.width()//2, 0))
            bounds = self.screen().availableGeometry()
            x = max(bounds.left(), min(origin.x()-self.hint.width()//2, bounds.right()-self.hint.width()+1))
            y = origin.y()-self.hint.height()-7
            if y < bounds.top():
                y = self.mapToGlobal(QPoint(0, self.height())).y()+7
            self.hint.move(x, min(y, bounds.bottom()-self.hint.height()+1))
            self.hint.show()
            self.hint_timer.start()
            QApplication.instance().installEventFilter(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.dismiss_hint()
        self.update()
        super().leaveEvent(event)

    def dismiss_hint(self):
        self.hint_timer.stop()
        if self.hint:
            hint, self.hint = self.hint, None
            QApplication.instance().removeEventFilter(self)
            hint.close()

    def check_hint_position(self):
        if self.hint and not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.dismiss_hint()

    def eventFilter(self, watched, event):
        if self.hint and event.type() == QEvent.MouseMove:
            if hasattr(event, 'globalPosition'):
                origin = self.mapToGlobal(QPoint(0, 0))
                if not QRectF(origin.x(), origin.y(), self.width(), self.height()).contains(event.globalPosition()):
                    self.dismiss_hint()
        return False

    def hideEvent(self, event):
        self.dismiss_hint()
        super().hideEvent(event)

    def event(self, event):
        if event.type() == QEvent.ToolTip:
            return True
        return super().event(event)


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
        command = '⌘' if app.hotkey_platform == 'mac' else 'Ctrl'
        choices = [
            (f"설정…                         {command}+,", app.toggle_settings),
            ("큰 시계로" if preferences.size == "compact" else "작은 시계로",
             lambda: app.set_preference("size", "large" if preferences.size == "compact" else "compact")),
            ("다크 테마로" if preferences.theme == "light" else "라이트 테마로",
             lambda: app.set_preference("theme", "dark" if preferences.theme == "light" else "light")),
            ("24시간제로" if preferences.hour_cycle == 12 else "12시간제로",
             lambda: app.set_preference("hour_cycle", 24 if preferences.hour_cycle == 12 else 12)),
            ("초 숨기기" if preferences.show_seconds else "초 표시",
             lambda: app.set_preference("show_seconds", not preferences.show_seconds)),
            ("트레이로 숨기기", app.hide_clock), ("위치 초기화", app.reset_position),
            ("프로그램 정보…                 F1", app.show_about), (f"종료                             {command}+Q", app.close),
        ]
        self.buttons = []
        for index, (text, callback) in enumerate(choices):
            control = button(text, lambda checked=False, action=callback: self.choose(action), self)
            control.setStyleSheet("text-align: left; padding: 7px 12px;")
            layout.addWidget(control)
            self.buttons.append(control)
            if text == '트레이로 숨기기':
                control.setEnabled(app.tray_available)
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
                              ("Return", self.activate)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.WindowShortcut)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        self.show()
        QApplication.instance().installEventFilter(self)
        self.buttons[0].setFocus()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress and hasattr(event, 'globalPosition'):
            if not self.frameGeometry().contains(event.globalPosition().toPoint()):
                self.close()
        return False

    def hideEvent(self, event):
        # Qt.Popup automatically hides on an outside click, without closeEvent.
        if self.app.popup_menu is self:
            self.app.popup_menu = None
        QApplication.instance().removeEventFilter(self)
        super().hideEvent(event)
        self.deleteLater()

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
