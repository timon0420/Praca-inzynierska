import cv2
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.camera import Camera
from app.websocket_sender import WebSocketSender


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.cap = None
        self.camera = None
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update_frame)
        self.loading = False
        self.websocket_sender = WebSocketSender()
        self.websocket_sender.start()
        self.init_ui()
        self.apply_style()

    def init_ui(self):
        self.setWindowTitle("Śledzenie dłoni")
        self.resize(1120, 740)
        self.setMinimumSize(900, 620)

        master = QHBoxLayout(self)
        master.setContentsMargins(24, 24, 24, 24)
        master.setSpacing(24)

        controls = QFrame()
        controls.setObjectName("controlPanel")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(24, 24, 24, 24)
        controls_layout.setSpacing(14)

        title = QLabel("Śledzenie dłoni")
        title.setObjectName("title")
        subtitle = QLabel("Sterowanie modelem manipulatora")
        subtitle.setObjectName("subtitle")

        source_label = QLabel("Źródło obrazu")
        source_label.setObjectName("fieldLabel")
        self.input = QLineEdit("0")
        self.input.setPlaceholderText("Numer kamery lub adres strumienia")

        self.start_camera_button = QPushButton("Uruchom kamerę")
        self.start_camera_button.setObjectName("startButton")
        self.start_camera_button.clicked.connect(self.start_camera)
        self.close_camera_button = QPushButton("Zatrzymaj kamerę")
        self.close_camera_button.setObjectName("stopButton")
        self.close_camera_button.clicked.connect(self.close_camera)
        self.close_camera_button.setEnabled(False)

        self.status = QLabel("Kamera jest wyłączona")
        self.status.setObjectName("statusNeutral")
        self.status.setWordWrap(True)

        data_title = QLabel("Dane dłoni")
        data_title.setObjectName("sectionTitle")
        self.position_label = QLabel("X: —     Y: —     Z: —")
        self.position_label.setObjectName("dataValue")
        self.angles_label = QLabel("Kąty Unity:\n—")
        self.angles_label.setObjectName("dataValue")
        self.angles_label.setWordWrap(True)

        controls_layout.addWidget(title)
        controls_layout.addWidget(subtitle)
        controls_layout.addSpacing(16)
        controls_layout.addWidget(source_label)
        controls_layout.addWidget(self.input)
        controls_layout.addWidget(self.start_camera_button)
        controls_layout.addWidget(self.close_camera_button)
        controls_layout.addWidget(self.status)
        controls_layout.addSpacing(14)
        controls_layout.addWidget(data_title)
        controls_layout.addWidget(self.position_label)
        controls_layout.addWidget(self.angles_label)
        controls_layout.addStretch()

        preview = QFrame()
        preview.setObjectName("previewPanel")
        preview_layout = QGridLayout(preview)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        self.image_label = QLabel("Podgląd kamery pojawi się tutaj")
        self.image_label.setObjectName("imagePlaceholder")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(600, 450)
        preview_layout.addWidget(self.image_label)

        master.addWidget(controls, 34)
        master.addWidget(preview, 66)

    def apply_style(self):
        self.setStyleSheet("""
            QWidget { background: #0f172a; color: #e2e8f0; font-family: "Segoe UI"; }
            QFrame#controlPanel, QFrame#previewPanel {
                background: #172033; border: 1px solid #26344d; border-radius: 14px;
            }
            QLabel#title { font-size: 27px; font-weight: 700; color: #f8fafc; }
            QLabel#subtitle { font-size: 14px; color: #94a3b8; }
            QLabel#fieldLabel, QLabel#sectionTitle { font-size: 14px; font-weight: 600; }
            QLabel#sectionTitle { font-size: 17px; color: #f8fafc; }
            QLineEdit {
                background: #0f172a; border: 1px solid #334155; border-radius: 7px;
                padding: 10px; font-size: 14px; selection-background-color: #2563eb;
            }
            QLineEdit:focus { border-color: #60a5fa; }
            QPushButton {
                border: 0; border-radius: 7px; padding: 11px 16px;
                font-size: 14px; font-weight: 600;
            }
            QPushButton#startButton { background: #2563eb; color: white; }
            QPushButton#startButton:hover { background: #1d4ed8; }
            QPushButton#stopButton { background: #334155; color: #e2e8f0; }
            QPushButton#stopButton:hover { background: #475569; }
            QPushButton:disabled { background: #202b3d; color: #64748b; }
            QLabel#statusNeutral, QLabel#statusLoading, QLabel#statusReady, QLabel#statusError {
                border-radius: 7px; padding: 10px; font-size: 13px;
            }
            QLabel#statusNeutral { background: #202b3d; color: #cbd5e1; }
            QLabel#statusLoading { background: #422006; color: #fde68a; }
            QLabel#statusReady { background: #052e24; color: #6ee7b7; }
            QLabel#statusError { background: #450a0a; color: #fecaca; }
            QLabel#dataValue {
                background: #0f172a; border: 1px solid #26344d;
                border-radius: 7px; padding: 11px; color: #cbd5e1;
            }
            QLabel#imagePlaceholder { color: #64748b; font-size: 17px; }
        """)

    def set_status(self, text, kind="Neutral"):
        self.status.setText(text)
        self.status.setObjectName(f"status{kind}")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def start_camera(self):
        if self.loading or self.cap is not None:
            return
        self.loading = True
        self.start_camera_button.setEnabled(False)
        self.input.setEnabled(False)
        self.set_status("Ładowanie kamery…", "Loading")
        QTimer.singleShot(0, self._initialize_camera)

    def _initialize_camera(self):
        source_text = self.input.text().strip()
        source = int(source_text) if source_text.isdigit() else source_text
        try:
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                cap.release()
                raise RuntimeError(f"Nie można otworzyć źródła obrazu: {source_text or '(puste)'}")
            self.cap = cap
            self.camera = Camera(QImage, cap)
            self.close_camera_button.setEnabled(True)
            self.timer.start()
        except Exception as error:
            self._release_resources()
            self.loading = False
            self.start_camera_button.setEnabled(True)
            self.input.setEnabled(True)
            self.set_status(str(error), "Error")

    def update_frame(self):
        try:
            qimage, tracking_data = self.camera.run_camera()
            if qimage is None:
                raise RuntimeError("Nie udało się odczytać klatki z kamery.")

            if self.loading:
                self.loading = False
                self.set_status("Kamera działa", "Ready")

            pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(
                pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._update_tracking_data(tracking_data)
        except Exception as error:
            self.close_camera(status_text=str(error), error=True)

    def _update_tracking_data(self, tracking_data):
        if tracking_data is None:
            self.position_label.setText("X: —     Y: —     Z: —")
            self.angles_label.setText("Kąty Unity:\n—")
            return

        x, y, z = tracking_data["position"].center_pixels
        angles = tracking_data["angles"]
        self.websocket_sender.send_angles(angles)
        self.position_label.setText(f"X: {x:.1f}px   Y: {y:.1f}px   Z: {z:.1f} wzgl.")
        self.angles_label.setText(
            "Kąty Unity:\n" + "  ·  ".join(f"{angle:.1f}°" for angle in angles)
        )

    def close_camera(self, checked=False, status_text=None, error=False):
        self._release_resources()
        self.loading = False
        self.start_camera_button.setEnabled(True)
        self.close_camera_button.setEnabled(False)
        self.input.setEnabled(True)
        self.image_label.clear()
        self.image_label.setText("Podgląd kamery pojawi się tutaj")
        self.position_label.setText("X: —     Y: —     Z: —")
        self.angles_label.setText("Kąty Unity:\n—")
        if status_text:
            self.set_status(status_text, "Error" if error else "Neutral")
        else:
            self.set_status("Kamera jest wyłączona", "Neutral")

    def _release_resources(self):
        self.timer.stop()
        if self.camera is not None:
            self.camera.close()
            self.camera = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def closeEvent(self, event):
        self._release_resources()
        self.websocket_sender.stop()
        super().closeEvent(event)
