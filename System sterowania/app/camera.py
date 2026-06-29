import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os

class Camera:
    def __init__(self, QImage, cap, mp):
        self.QImage = QImage
        self.cap = cap

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.CONNECTIONS = [
            (0,1), (1,2), (2,3), (3,4),             #Kciuk
            (0,5), (5,6), (6,7), (7,8),             #Palec wskazujący
            (0,9), (9,10), (10,11), (11,12),        #Palec środkowy
            (0,13), (13,14), (14,15), (15,16),      #Palec serdeczny
            (0,17), (17,18), (18,19), (19,20),      #Palec mały
        ]

        base_options = python.BaseOptions(
            model_asset_path="hand_landmarker.task",
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            min_hand_presence_confidence=0.7
        )

        self.detector = vision.HandLandmarker.create_from_options(options)

    def run_camera(self):
        self.ret, self.frame = self.cap.read()
        self.frame = cv2.flip(self.frame, 1)
        
        if not self.ret:
            return None
        
        self.frame = self.hand_tracking()
        
        self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        h, w, ch = self.frame.shape
        bytesPerLine = ch * w

        qimg = self.QImage(self.frame.data, w, h, bytesPerLine, self.QImage.Format.Format_RGB888)

        return qimg
    
    def hand_tracking(self):
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=self.frame)

        results = self.detector.detect(mp_image)

        if results.hand_landmarks:
            for hand in results.hand_landmarks:
                points = []
                for landmark in hand:
                    x = int(landmark.x * self.frame.shape[1])
                    y = int(landmark.y * self.frame.shape[0])
                    points.append((x, y))
                    cv2.circle(self.frame, (x, y), 5, (0, 255, 0), -1)
        
                for start, end in self.CONNECTIONS:
                    cv2.line(self.frame, points[start], points[end], (0, 255, 0), 2)

            for hand_id, hand in enumerate(results.hand_landmarks):
                print(f"Hand {hand_id}:")

                for landmark in hand:
                    x = int(landmark.x * self.frame.shape[1])
                    y = int(landmark.y * self.frame.shape[0])
                    print(f"({x}, {y})")

        return self.frame