"""Draw the original clock emblem; create PNG, ICO and ICNS without extra tools."""
import struct
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter, QPen, QColor, QGuiApplication


def png(size):
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 256, size / 256)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor('#137A70'))
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 54, 54)
    p.setBrush(QColor('#F8FAFC'))
    p.drawEllipse(QRectF(43, 43, 170, 170))
    p.setPen(QPen(QColor('#CADAD7'), 7, Qt.SolidLine, Qt.RoundCap))
    for a, b in ((QPointF(128, 58), QPointF(128, 67)), (QPointF(198, 128), QPointF(189, 128)),
                 (QPointF(128, 198), QPointF(128, 189)), (QPointF(58, 128), QPointF(67, 128))):
        p.drawLine(a, b)
    p.setPen(QPen(QColor('#172538'), 12, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(128, 128), QPointF(128, 83))
    p.drawLine(QPointF(128, 128), QPointF(165, 149))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor('#137A70'))
    p.drawEllipse(QRectF(119, 119, 18, 18))
    p.end()
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    image.save(buf, 'PNG')
    return bytes(buf.data())


def main():
    app = QGuiApplication.instance() or QGuiApplication([])
    assets = Path(__file__).resolve().parent / 'assets'
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [png(size) for size in sizes]
    offset = 6 + 16 * len(sizes)
    entries = []
    for size, data in zip(sizes, images):
        entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (assets/'icon.ico').write_bytes(struct.pack('<HHH', 0, 1, len(sizes)) + b''.join(entries) + b''.join(images))
    chunks = []
    for tag, size in ((b'icp4', 16), (b'icp5', 32), (b'icp6', 64), (b'ic07', 128),
                      (b'ic08', 256), (b'ic09', 512), (b'ic10', 1024)):
        data = png(size)
        chunks.append(tag + struct.pack('>I', len(data) + 8) + data)
    body = b''.join(chunks)
    (assets/'icon.icns').write_bytes(b'icns' + struct.pack('>I', len(body)+8) + body)
    (assets/'icon.png').write_bytes(png(256))
    print('Generated shared PNG, multi-resolution ICO and ICNS icons')


if __name__ == '__main__':
    main()
