"""Per-user single instance with a local socket; no network service."""
import hashlib
from PySide6.QtCore import QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from settings import settings_path


class InstanceGate:
    def __init__(self):
        folder = settings_path().parent
        folder.mkdir(parents=True, exist_ok=True)
        self.name = 'FloatingClock-' + hashlib.sha256(str(folder.resolve()).encode()).hexdigest()[:24]
        self.lock = QLockFile(str(folder / 'instance.lock'))
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer()
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self.receive)
        self.callback = None
        self.pending = False
        self.owner = False
        self.connections = []

    def claim(self):
        self.owner = self.lock.tryLock(0)
        if not self.owner:
            return False
        QLocalServer.removeServer(self.name)
        if not self.server.listen(self.name):
            self.lock.unlock()
            self.owner = False
            raise OSError('Cannot start local clock instance channel: ' + self.server.errorString())
        return True

    def notify(self):
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if not socket.waitForConnected(2500):
            return False
        socket.write(b'show')
        socket.flush()
        socket.waitForBytesWritten(1000)
        ok = socket.waitForReadyRead(2500) or socket.bytesAvailable() > 0
        response = bytes(socket.readAll()) if ok else b''
        socket.close()
        return response == b'ok'

    def receive(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self.connections.append(socket)
            socket.readyRead.connect(lambda s=socket: self.dispatch(s))
            socket.disconnected.connect(lambda s=socket: self.release_connection(s))
            if socket.bytesAvailable():
                self.dispatch(socket)

    def dispatch(self, socket):
        if bytes(socket.readAll()) == b'show':
            if self.callback:
                self.callback()
            else:
                self.pending = True
            socket.write(b'ok')
            socket.flush()
        socket.disconnectFromServer()

    def release_connection(self, socket):
        if socket in self.connections:
            self.connections.remove(socket)
        socket.deleteLater()

    def activate(self, callback):
        self.callback = callback
        if self.pending:
            self.pending = False
            callback()

    def close(self):
        if self.owner:
            self.server.close()
            self.lock.unlock()
            self.owner = False
