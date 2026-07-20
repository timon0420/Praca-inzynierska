import json
import unittest
from unittest.mock import patch

from app.websocket_sender import WebSocketSender


class WebSocketSenderTests(unittest.TestCase):
    def test_payload_matches_server_contract(self):
        sender = WebSocketSender()
        with patch("app.websocket_sender.time.time", return_value=123.5):
            sender.send_angles([0, 30, 60, 90, 120, 180])
        payload = json.loads(sender._messages.get_nowait())
        self.assertEqual(payload["angles"], [0, 30, 60, 90, 120, 180])
        self.assertEqual(payload["timestamp"], 123.5)

    def test_only_latest_payload_is_queued(self):
        sender = WebSocketSender()
        sender.send_angles([0] * 6)
        sender.send_angles([180] * 6)
        payload = json.loads(sender._messages.get_nowait())
        self.assertEqual(payload["angles"], [180] * 6)

    def test_rejects_invalid_angles(self):
        sender = WebSocketSender()
        with self.assertRaises(ValueError):
            sender.send_angles([0] * 5)
        with self.assertRaises(ValueError):
            sender.send_angles([0, 0, 0, 0, 0, 181])

    def test_client_frames_are_masked_text_frames(self):
        frame = WebSocketSender._create_text_frame("test")
        self.assertEqual(frame[0], 0x81)
        self.assertTrue(frame[1] & 0x80)


if __name__ == "__main__":
    unittest.main()
