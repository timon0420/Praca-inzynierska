from __future__ import annotations

import threading
import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from backend.hand_position import HandPositionCalculator


class HandAnalyzer:
    def __init__(self, model_path: str):
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.3,
            min_tracking_confidence=0.3,
            min_hand_presence_confidence=0.3,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.calculator = HandPositionCalculator()
        self.last_landmarks = None
        self.last_detection_at = 0.0
        self.last_used_at = time.monotonic()
        self._last_timestamp_ms = -1
        self._lock = threading.Lock()

    def analyze(self, jpeg: bytes) -> dict:
        started = time.perf_counter()
        encoded = np.frombuffer(jpeg, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Nie można zdekodować obrazu JPEG.")

        with self._lock:
            self.last_used_at = time.monotonic()
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = max(
                int(time.monotonic() * 1000), self._last_timestamp_ms + 1
            )
            self._last_timestamp_ms = timestamp_ms
            results = self.detector.detect_for_video(image, timestamp_ms)

            now = time.monotonic()
            if results.hand_landmarks:
                self.last_landmarks = results.hand_landmarks[0]
                self.last_detection_at = now
            elif now - self.last_detection_at > 0.25:
                self.last_landmarks = None

            response = {
                "detected": self.last_landmarks is not None,
                "processingMs": round((time.perf_counter() - started) * 1000, 2),
            }
            if self.last_landmarks is None:
                return response

            height, width = frame.shape[:2]
            position = self.calculator.calculate_position(
                self.last_landmarks, width, height
            )
            response["angles"] = self.calculator.pixels_to_angles(
                position, width, height
            )
            response["position"] = {
                "center": [round(value, 2) for value in position.center_pixels],
                "orientation": [
                    round(value, 2) for value in position.orientation_degrees
                ],
            }
            response["processingMs"] = round(
                (time.perf_counter() - started) * 1000, 2
            )
            return response

    def close(self) -> None:
        with self._lock:
            if self.detector is not None:
                self.detector.close()
                self.detector = None


class AnalyzerRegistry:
    def __init__(self, model_path: str, idle_ttl_seconds: float = 300.0):
        self.model_path = model_path
        self.idle_ttl_seconds = idle_ttl_seconds
        self._analyzers: dict[str, HandAnalyzer] = {}
        self._lock = threading.Lock()

    def analyze(self, session_code: str, jpeg: bytes) -> dict:
        with self._lock:
            analyzer = self._analyzers.get(session_code)
            if analyzer is None:
                analyzer = HandAnalyzer(self.model_path)
                self._analyzers[session_code] = analyzer
        return analyzer.analyze(jpeg)

    def cleanup(self) -> int:
        deadline = time.monotonic() - self.idle_ttl_seconds
        with self._lock:
            expired = [
                session_code
                for session_code, analyzer in self._analyzers.items()
                if analyzer.last_used_at < deadline
            ]
            analyzers = [self._analyzers.pop(session_code) for session_code in expired]
        for analyzer in analyzers:
            analyzer.close()
        return len(analyzers)

    def close(self) -> None:
        with self._lock:
            analyzers = list(self._analyzers.values())
            self._analyzers.clear()
        for analyzer in analyzers:
            analyzer.close()
