import os

import cv2
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
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
from app.websocket_sender import SessionWebSocketClient


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.cap = None
        self.camera = None
        self.session_client = None
        self.loading = False
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update_frame)
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
        controls_layout.setSpacing(12)

        title = QLabel("Śledzenie dłoni")
        title.setObjectName("title")
        subtitle = QLabel("Sterowanie modelem manipulatora")
        subtitle.setObjectName("subtitle")

        server_label = QLabel("Adres serwera")
        server_label.setObjectName("fieldLabel")
        self.server_input = QLineEdit(os.environ.get(
            "CONTROL_SERVER_URL", "https://websocket-inzynierka.onrender.com"
        ))

        code_label = QLabel("Kod sesji")
        code_label.setObjectName("fieldLabel")
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("np. 7K4M-P2QX")
        self.code_input.setMaxLength(9)

        source_label = QLabel("Źródło obrazu")
        source_label.setObjectName("fieldLabel")
        self.source_combo = QComboBox()
        self.source_combo.addItem("Kamera lokalna", "local_camera")
        self.source_combo.addItem("Kamera z aplikacji webowej", "web_camera")
        self.source_combo.currentIndexChanged.connect(self._source_changed)

        camera_label = QLabel("Numer kamery")
        camera_label.setObjectName("fieldLabel")
        self.camera_input = QLineEdit("0")
        self.camera_input.setPlaceholderText("Numer kamery, np. 0")

        self.start_camera_button = QPushButton("Połącz i uruchom")
        self.start_camera_button.setObjectName("startButton")
        self.start_camera_button.clicked.connect(self.start_camera)
        self.close_camera_button = QPushButton("Zatrzymaj")
        self.close_camera_button.setObjectName("stopButton")
        self.close_camera_button.clicked.connect(self.close_camera)
        self.close_camera_button.setEnabled(False)

        self.status = QLabel("Wpisz kod sesji wygenerowany na stronie")
        self.status.setObjectName("statusNeutral")
        self.status.setWordWrap(True)

        data_title = QLabel("Dane dłoni")
        data_title.setObjectName("sectionTitle")
        self.position_label = QLabel("X: —     Y: —     Z: —")
        self.position_label.setObjectName("dataValue")
        self.angles_label = QLabel("Kąty Unity:\n—")
        self.angles_label.setObjectName("dataValue")
        self.angles_label.setWordWrap(True)

        for widget in (title, subtitle, server_label, self.server_input, code_label,
                       self.code_input, source_label, self.source_combo, camera_label,
                       self.camera_input, self.start_camera_button,
                       self.close_camera_button, self.status, data_title,
                       self.position_label, self.angles_label):
            controls_layout.addWidget(widget)
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
            QLabel#subtitle { font-size: 14px; color: #94a3b8; margin-bottom: 8px; }
            QLabel#fieldLabel, QLabel#sectionTitle { font-size: 13px; font-weight: 600; }
            QLabel#sectionTitle { font-size: 17px; color: #f8fafc; margin-top: 6px; }
            QLineEdit, QComboBox {
                background: #0f172a; border: 1px solid #334155; border-radius: 7px;
                padding: 8px; font-size: 13px; selection-background-color: #2563eb;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #60a5fa; }
            QComboBox QAbstractItemView { background: #172033; selection-background-color: #2563eb; }
            QPushButton {
                border: 0; border-radius: 7px; padding: 10px 16px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton#startButton { background: #2563eb; color: white; }
            QPushButton#startButton:hover { background: #1d4ed8; }
            QPushButton#stopButton { background: #334155; color: #e2e8f0; }
            QPushButton#stopButton:hover { background: #475569; }
            QPushButton:disabled, QLineEdit:disabled, QComboBox:disabled {
                background: #202b3d; color: #64748b;
            }
            QLabel#statusNeutral, QLabel#statusLoading, QLabel#statusReady, QLabel#statusError {
                border-radius: 7px; padding: 9px; font-size: 12px;
            }
            QLabel#statusNeutral { background: #202b3d; color: #cbd5e1; }
            QLabel#statusLoading { background: #422006; color: #fde68a; }
            QLabel#statusReady { background: #052e24; color: #6ee7b7; }
            QLabel#statusError { background: #450a0a; color: #fecaca; }
            QLabel#dataValue {
                background: #0f172a; border: 1px solid #26344d;
                border-radius: 7px; padding: 9px; color: #cbd5e1;
            }
            QLabel#imagePlaceholder { color: #64748b; font-size: 17px; }
        """)

    def _source_changed(self):
        is_local = self.source_combo.currentData() == "local_camera"
        self.camera_input.setEnabled(is_local and not self.timer.isActive())

    def set_status(self, text, kind="Neutral"):
        self.status.setText(text)
        self.status.setObjectName(f"status{kind}")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def start_camera(self):
        if self.loading or self.timer.isActive():
            return
        code = self.code_input.text().strip()
        source = self.source_combo.currentData()
        if not code and source == "web_camera":
            self.set_status("Kamera webowa wymaga kodu sesji ze strony.", "Error")
            return
        self.loading = True
        self._set_controls_enabled(False)
        self.set_status(
            "Tworzenie sesji dla kamery lokalnej…" if not code else "Parowanie z sesją…",
            "Loading",
        )
        QTimer.singleShot(0, self._initialize_source)

    def _initialize_source(self):
        source = self.source_combo.currentData()
        try:
            if self.session_client is None:
                self.session_client = SessionWebSocketClient(self.server_input.text().strip())
            self.session_client.start(self.code_input.text(), source)

            if source == "local_camera":
                source_text = self.camera_input.text().strip()
                camera_index = int(source_text) if source_text.isdigit() else source_text
                cap = cv2.VideoCapture(camera_index)
                if not cap.isOpened():
                    cap.release()
                    raise RuntimeError(f"Nie można otworzyć kamery: {source_text or '(puste)'}")
                self.cap = cap
                self.camera = Camera(QImage, cap)
            else:
                self.camera = Camera(QImage)

            self.close_camera_button.setEnabled(True)
            self.timer.start()
        except Exception as error:
            self._release_resources(stop_client=True)
            self.loading = False
            self._set_controls_enabled(True)
            self.set_status(str(error), "Error")

    def update_frame(self):
        try:
            if self.session_client and self.session_client.session_code and not self.code_input.text():
                self.code_input.setText(self.session_client.session_code)
            if self.session_client and self.session_client.last_error and not self.session_client.connected:
                self.set_status(self.session_client.last_error, "Error")

            if self.source_combo.currentData() == "local_camera":
                qimage, tracking_data = self.camera.run_camera()
                if qimage is None:
                    raise RuntimeError("Nie udało się odczytać klatki z kamery.")
            else:
                jpeg = self.session_client.get_latest_frame()
                if jpeg is None:
                    self.set_status(
                        "Połączono. Oczekiwanie na obraz z aplikacji webowej…"
                        if self.session_client.connected else "Łączenie z serwerem…",
                        "Ready" if self.session_client.connected else "Loading",
                    )
                    return
                qimage, tracking_data = self.camera.process_jpeg(jpeg)
                if qimage is None:
                    return

            if self.loading or self.status.objectName() != "statusReady":
                self.loading = False
                self.set_status("Kamera działa — sesja połączona", "Ready")

            pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
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
        self.position_label.setText(f"X: {x:.1f}px   Y: {y:.1f}px   Z: {z:.1f} wzgl.")
        self.angles_label.setText("Kąty Unity:\n" + "  ·  ".join(f"{angle:.1f}°" for angle in angles))
        try:
            self.session_client.send_angles(angles)
        except Exception as error:
            # Obliczenia i podgląd nie mogą zależeć od stanu połączenia.
            self.set_status(f"Kąty obliczone; błąd wysyłania: {error}", "Error")

    def close_camera(self, checked=False, status_text=None, error=False):
        del checked
        self._release_resources(stop_client=True)
        self.loading = False
        self._set_controls_enabled(True)
        self.close_camera_button.setEnabled(False)
        self.image_label.clear()
        self.image_label.setText("Podgląd kamery pojawi się tutaj")
        self.position_label.setText("X: —     Y: —     Z: —")
        self.angles_label.setText("Kąty Unity:\n—")
        self.set_status(status_text or "Kamera jest wyłączona", "Error" if error else "Neutral")

    def _set_controls_enabled(self, enabled):
        self.start_camera_button.setEnabled(enabled)
        self.server_input.setEnabled(enabled)
        self.code_input.setEnabled(enabled)
        self.source_combo.setEnabled(enabled)
        self.camera_input.setEnabled(enabled and self.source_combo.currentData() == "local_camera")

    def _release_resources(self, stop_client=False):
        self.timer.stop()
        if self.camera is not None:
            self.camera.close()
            self.camera = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if stop_client and self.session_client is not None:
            self.session_client.stop()

    def closeEvent(self, event):
        self._release_resources(stop_client=True)
        super().closeEvent(event)
