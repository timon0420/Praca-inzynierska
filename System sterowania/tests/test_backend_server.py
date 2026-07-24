import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from backend.server import AnalysisHandler


class FakeRegistry:
    def __init__(self):
        self.calls = []

    def analyze(self, session_code, jpeg):
        self.calls.append((session_code, jpeg))
        return {
            "detected": True,
            "angles": [10, 20, 30, 40, 50, 60],
            "processingMs": 4.5,
        }


class AnalysisServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = FakeRegistry()
        AnalysisHandler.registry = cls.registry
        AnalysisHandler.internal_token = "test-token"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AnalysisHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response.status, payload

    def test_healthcheck(self):
        status, _ = self.request("GET", "/healthz")
        self.assertEqual(status, 204)

    def test_valid_jpeg_is_analyzed(self):
        jpeg = b"\xff\xd8data\xff\xd9"
        status, payload = self.request(
            "POST",
            "/analyze",
            jpeg,
            {
                "Content-Type": "image/jpeg",
                "Content-Length": str(len(jpeg)),
                "X-Session-Code": "ABCD-EFGH",
                "X-Internal-Token": "test-token",
            },
        )
        self.assertEqual(status, 200)
        result = json.loads(payload)
        self.assertTrue(result["detected"])
        self.assertEqual(result["angles"][-1], 60)

    def test_authentication_and_content_type_are_required(self):
        jpeg = b"\xff\xd8data\xff\xd9"
        common = {
            "Content-Length": str(len(jpeg)),
            "X-Session-Code": "ABCD-EFGH",
        }
        status, _ = self.request(
            "POST", "/analyze", jpeg, {**common, "Content-Type": "image/jpeg"}
        )
        self.assertEqual(status, 401)
        status, _ = self.request(
            "POST",
            "/analyze",
            jpeg,
            {
                **common,
                "Content-Type": "application/octet-stream",
                "X-Internal-Token": "test-token",
            },
        )
        self.assertEqual(status, 415)

    def test_valid_session_code_is_required(self):
        jpeg = b"\xff\xd8data\xff\xd9"
        for session_code in ("", "ABCD1234", "abcd-efgh", "ABCI-EFGH"):
            status, _ = self.request(
                "POST",
                "/analyze",
                jpeg,
                {
                    "Content-Type": "image/jpeg",
                    "Content-Length": str(len(jpeg)),
                    "X-Session-Code": session_code,
                    "X-Internal-Token": "test-token",
                },
            )
            self.assertEqual(status, 400, session_code)

    def test_session_code_is_forwarded_to_registry(self):
        jpeg = b"\xff\xd8data\xff\xd9"
        for session_code in ("ABCD-EFGH", "1234-WXYZ"):
            status, _ = self.request(
                "POST",
                "/analyze",
                jpeg,
                {
                    "Content-Type": "image/jpeg",
                    "Content-Length": str(len(jpeg)),
                    "X-Session-Code": session_code,
                    "X-Internal-Token": "test-token",
                },
            )
            self.assertEqual(status, 200)
        self.assertEqual(
            [call[0] for call in self.registry.calls[-2:]],
            ["ABCD-EFGH", "1234-WXYZ"],
        )

    def test_invalid_jpeg_is_rejected(self):
        body = b"not-a-jpeg"
        status, _ = self.request(
            "POST",
            "/analyze",
            body,
            {
                "Content-Type": "image/jpeg",
                "Content-Length": str(len(body)),
                "X-Session-Code": "ABCD-EFGH",
                "X-Internal-Token": "test-token",
            },
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
