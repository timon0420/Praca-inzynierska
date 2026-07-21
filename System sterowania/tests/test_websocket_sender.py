import json
import unittest
from unittest.mock import patch

from app.websocket_sender import SessionWebSocketClient


class SessionWebSocketClientTests(unittest.TestCase):
    def test_payload_matches_server_contract(self):
        client = SessionWebSocketClient("http://localhost:8080")
        with patch("app.websocket_sender.time.time", return_value=123.5):
            client.send_angles([0, 30, 60, 90, 120, 180])
        payload = json.loads(client._outbound.get_nowait())
        self.assertEqual(payload["type"], "angles")
        self.assertEqual(payload["angles"], [0, 30, 60, 90, 120, 180])
        self.assertEqual(payload["timestamp"], 123.5)
        self.assertEqual(payload["sequence"], 1)

    def test_only_latest_payload_and_frame_are_queued(self):
        client = SessionWebSocketClient()
        client.send_angles([0] * 6)
        client.send_angles([180] * 6)
        self.assertEqual(json.loads(client._outbound.get_nowait())["angles"], [180] * 6)
        client._put_latest_frame(b"old")
        client._put_latest_frame(b"new")
        self.assertEqual(client.get_latest_frame(), b"new")

    def test_rejects_invalid_angles_and_source(self):
        client = SessionWebSocketClient()
        with self.assertRaises(ValueError):
            client.send_angles([0] * 5)
        with self.assertRaises(ValueError):
            client.send_angles([0, 0, 0, 0, 0, 181])
        with self.assertRaises(ValueError):
            client.set_source("invalid")

    def test_local_camera_can_start_without_existing_code(self):
        client = SessionWebSocketClient()
        with patch.object(client, "_thread_main"):
            client.start("", "local_camera")
            client._thread.join(timeout=1)
        self.assertEqual(client._code, "")

    def test_web_camera_requires_existing_code(self):
        client = SessionWebSocketClient()
        with self.assertRaises(ValueError):
            client.start("", "web_camera")

    def test_builds_ws_and_wss_urls(self):
        client = SessionWebSocketClient("https://example.test")
        client._token = "abc"
        self.assertEqual(client._websocket_url(), "wss://example.test/ws/python?token=abc")
        client.api_url = "http://localhost:8080"
        self.assertEqual(client._websocket_url(), "ws://localhost:8080/ws/python?token=abc")


if __name__ == "__main__":
    unittest.main()
