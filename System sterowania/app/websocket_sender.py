from __future__ import annotations
import base64
import hashlib
import json
import os
import queue
import socket
import ssl
import struct
import threading
import time
from urllib.parse import urlparse


class WebSocketSender:

    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(
        self,
        url: str = "wss://websocket-inzynierka.onrender.com/ws",
        reconnect_delay: float = 2.0,
        connect_timeout: float = 1.0,
    ):
        self.url = url
        self.reconnect_delay = reconnect_delay
        self.connect_timeout = connect_timeout
        self._messages: queue.Queue[str] = queue.Queue(maxsize=1)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: socket.socket | None = None
        self.connected = False
        self.last_error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="websocket-sender", daemon=True
        )
        self._thread.start()

    def send_angles(self, angles: list[float] | tuple[float, ...]) -> None:
        if len(angles) != 6:
            raise ValueError("WebSocket wymaga dokładnie sześciu kątów.")
        values = [float(angle) for angle in angles]
        if not all(0.0 <= angle <= 180.0 for angle in values):
            raise ValueError("Każdy kąt musi należeć do zakresu 0–180°.")
        message = json.dumps(
            {"angles": values, "timestamp": time.time()}, separators=(",", ":")
        )
        try:
            self._messages.put_nowait(message)
        except queue.Full:
            try:
                self._messages.get_nowait()
            except queue.Empty:
                pass
            self._messages.put_nowait(message)

    def stop(self) -> None:
        self._stop_event.set()
        sock = self._socket
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._socket = None
        self.connected = False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._socket = self._connect()
                self.connected = True
                self.last_error = None
                self._send_loop(self._socket)
            except (OSError, ValueError, ConnectionError) as error:
                self.last_error = str(error)
            finally:
                self.connected = False
                if self._socket is not None:
                    try:
                        self._socket.close()
                    except OSError:
                        pass
                    self._socket = None
            self._stop_event.wait(self.reconnect_delay)

    def _connect(self) -> socket.socket:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
            raise ValueError(
                "Obsługiwane są adresy ws:// lub wss://host:port/ścieżka."
            )

        secure = parsed.scheme == "wss"
        port = parsed.port or (443 if secure else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        raw_sock = socket.create_connection(
            (parsed.hostname, port), timeout=self.connect_timeout
        )
        if secure:
            context = ssl.create_default_context()
            sock = context.wrap_socket(raw_sock, server_hostname=parsed.hostname)
        else:
            sock = raw_sock

        sock.settimeout(self.connect_timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        default_port = 443 if secure else 80
        host_header = (
            parsed.hostname
            if port == default_port
            else f"{parsed.hostname}:{port}"
        )
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = self._receive_headers(sock)
        status_line = response.split("\r\n", 1)[0]
        if " 101 " not in status_line:
            sock.close()
            raise ConnectionError(f"Serwer odrzucił WebSocket: {status_line}")

        headers = {}
        for line in response.split("\r\n")[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        expected = base64.b64encode(
            hashlib.sha1((key + self.GUID).encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            sock.close()
            raise ConnectionError("Nieprawidłowa odpowiedź uzgadniania WebSocket.")
        sock.settimeout(0.2)
        return sock

    def _send_loop(self, sock: socket.socket) -> None:
        while not self._stop_event.is_set():
            try:
                message = self._messages.get(timeout=0.2)
            except queue.Empty:
                self._drain_incoming(sock)
                continue
            sock.sendall(self._create_text_frame(message))
            self._drain_incoming(sock)

    @staticmethod
    def _drain_incoming(sock: socket.socket) -> None:
        try:
            sock.setblocking(False)
            sock.recv(4096)
        except (BlockingIOError, socket.timeout):
            pass
        finally:
            sock.settimeout(0.2)

    @staticmethod
    def _receive_headers(sock: socket.socket) -> str:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("Serwer zamknął połączenie podczas uzgadniania.")
            data.extend(chunk)
            if len(data) > 65536:
                raise ConnectionError("Odpowiedź WebSocket jest zbyt duża.")
        return data.decode("latin-1")

    @staticmethod
    def _create_text_frame(message: str) -> bytes:
        payload = message.encode("utf-8")
        mask = os.urandom(4)
        length = len(payload)
        header = bytearray([0x81])
        if length < 126:
            header.append(0x80 | length)
        elif length <= 65535:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return bytes(header) + masked
