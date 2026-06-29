import mediapipe as mp
import cv2
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLineEdit, QTextEdit
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from app.camera import Camera

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.style()

    def ui_elements(self):
        self.title = QLabel("Hand Tracking")
        self.subtitle = QLabel("Zacznij od uruchomienia kamery")
        self.input = QLineEdit(parent=self)
        self.input.setPlaceholderText("Źródło obrazu")
        self.input.setText("0")
        self.message = QTextEdit("Zacznij od uruchomienia kamery")
        self.message.setReadOnly(True)


    def init_ui(self):
        self.setWindowTitle("Hand Tracking")
        self.ui_elements()
        self.button_events()
        self.resize(1000, 700)

        self.master = QHBoxLayout(self)
        self.master.setContentsMargins(20, 20, 20, 20)
        self.master.setSpacing(20)

        self.col1 = QVBoxLayout()
        self.col1.setSpacing(15)

        self.col2 = QVBoxLayout()
        self.col2.setSpacing(15)

        self.master.addLayout(self.col1)
        self.master.addLayout(self.col2)

        self.image_label = QLabel()
        self.image_label.setScaledContents(True)
        self.image_label.setMinimumSize(640, 480)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.start_camera_button)
        button_layout.addWidget(self.close_camera_button)

        self.col1.addWidget(self.title)
        self.col1.addWidget(self.subtitle)
    
        input_layout = QVBoxLayout()
        input_layout.addWidget(self.message)
        input_layout.addWidget(self.input)

        self.col1.addLayout(input_layout)

        self.col1.addLayout(button_layout)

        self.col2.addWidget(self.image_label)

        self.master.addLayout(self.col1, 30)
        self.master.addLayout(self.col2, 70)

    def button_events(self):
        self.start_camera_button = QPushButton("Uruchomienie Kamery", clicked=lambda: self.start_camera(int(self.input.text()) if self.input.text().isdigit() else self.input.text()))
        self.close_camera_button = QPushButton("Zamknięcie Kamery", clicked=lambda: self.close_camera())

    def style(self): 
        self.setStyleSheet("""

        QPushButton {
            background-color: #4CAF50;
            cursor: pointer;
            border-radius: 5px;
            padding: 10px 20px;
            font-size: 16px;
        }

        QPushButton:hover {
            background-color: #45a049;
        }

        QPushButton:pressed {
            background-color: #3e8e41;
            box-shadow: 0 3px #666;
            transform: translateY(4px);
        }

        """)

        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title.setStyleSheet("""
        font-size: 24px;
        font-weight: bold;
        """)

        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.subtitle.setStyleSheet("""
        font-size: 18px;
        font-weight: bold;
        """)

    def start_camera(self, source=0):
        try:
            self.cap = cv2.VideoCapture(source)
            self.camera = Camera(QImage, self.cap, mp)
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)
        except Exception as e:
            self.message.setText(str(e))
            QTimer.singleShot(3000, lambda: self.message.setText("Zacznij od uruchomienia kamery"))

    def update_frame(self):
        q_img = self.camera.run_camera()
        if q_img:
            self.image_label.setPixmap(QPixmap.fromImage(q_img))

    def close_camera(self):
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
            self.cap = None
            self.image_label.setPixmap(QPixmap())
            if hasattr(self, 'timer'):
                self.timer.stop()

    def close_event(self, event):
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        super().close_event(event)

