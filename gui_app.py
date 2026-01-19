import sys
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QCheckBox, 
                             QSlider, QGroupBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QPalette, QColor, QImage, QPixmap

import numpy as np
import os
import subprocess
import sys

from state import AppState
from engine import DirectorEngine

# --- Premium Dark Theme Stylesheet ---
DARK_THEME_STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
}
QWidget {
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}
QGroupBox {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    border-radius: 8px;
    margin-top: 20px;
    font-weight: bold;
    color: #00bcd4; /* Teal Accent */
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    margin-left: 10px;
}
QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    border-radius: 6px;
    padding: 8px 16px;
    color: white;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #3e3e3e;
    border-color: #00bcd4;
}
QPushButton:pressed {
    background-color: #1e1e1e;
}
QPushButton:disabled {
    background-color: #1a1a1a;
    color: #555;
    border-color: #2d2d2d;
}
/* Start Button Special Style */
QPushButton#btn_start {
    background-color: #009688; /* Teal-Green */
    border: none;
}
QPushButton#btn_start:hover {
    background-color: #26a69a;
}
QPushButton#btn_start:disabled {
    background-color: #2d2d2d;
    color: #555;
}
/* Stop Button Special Style */
QPushButton#btn_stop {
    background-color: #d32f2f; /* Red */
    border: none;
}
QPushButton#btn_stop:hover {
    background-color: #e57373;
}
QPushButton#btn_stop:disabled {
    background-color: #2d2d2d;
    color: #555;
}

QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #555;
    background: #1e1e1e;
}
QCheckBox::indicator:checked {
    background-color: #00bcd4;
    border-color: #00bcd4;
    image: url(none); /* We could add a checkmark icon here */
}
QCheckBox::indicator:hover {
    border-color: #00bcd4;
}

QSlider::groove:horizontal {
    border: 1px solid #3e3e3e;
    height: 6px;
    background: #1e1e1e;
    margin: 2px 0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #00bcd4;
    border: 1px solid #00bcd4;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #4dd0e1;
}

QLabel {
    color: #cccccc;
}
"""

class ControlPanel(QMainWindow):
    frame_update_signal = pyqtSignal(object)

    def __init__(self, state, engine):
        super().__init__()
        self.state = state
        self.engine = engine
        self.engine_thread = None
        
        self.setWindowTitle("AutoDirector")
        self.setGeometry(100, 100, 420, 700)
        
        # Apply Stylesheet
        self.setStyleSheet(DARK_THEME_STYLESHEET)
        
        # Connect Signal
        self.frame_update_signal.connect(self.update_image_slot)
        
        # Main Layout (Scroll Area Wrapper)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # scroll.setStyleSheet("background-color: transparent;") # Optional
        
        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        scroll.setWidget(container)
        self.setCentralWidget(scroll)
        
        # Title Matches Container Layout
        title = QLabel("AutoDirector Control")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        self.layout.addWidget(title)
        
        # --- VIDEO VIEWPORT ---
        self.video_label = QLabel("Waiting for Camera...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(400, 300)
        self.video_label.setStyleSheet("background-color: #000; border: 2px solid #00bcd4; border-radius: 4px;")
        self.layout.addWidget(self.video_label)

        # --- Section 1: Actions ---
        action_layout = QHBoxLayout()
        action_layout.setSpacing(15)
        
        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setMinimumHeight(45)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_engine)
        
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setMinimumHeight(45)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.stop_engine)
        self.btn_stop.setEnabled(False)
        
        action_layout.addWidget(self.btn_start)
        action_layout.addWidget(self.btn_stop)
        self.layout.addLayout(action_layout)
        
        # --- Section 2: Devices ---
        dev_group = QGroupBox("Connected Devices")
        dev_layout = QVBoxLayout()
        dev_layout.setSpacing(10)
        dev_layout.setContentsMargins(15, 25, 15, 15) # Top margin for title
        
        self.cam_checks = {}
        self.mic_checks = {}
        
        # Header Row
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Camera"))
        header_row.addWidget(QLabel("Microphone"))
        dev_layout.addLayout(header_row)
        
        # Scan for devices
        try:
             available_devices = self.engine.scan_devices()
        except Exception as e:
             print(f"Scan failed: {e}")
             available_devices = {}
        
        if not available_devices:
             dev_layout.addWidget(QLabel("No configured devices found."))
        
        for idx in sorted(available_devices.keys()): 
            info = available_devices[idx]
            role = info['role']
            cam_ok = info['cam_found']
            mic_ok = info['mic_found']
            mic_name = info['mic_name']
            
            row = QHBoxLayout()
            
            # Camera Checkbox
            c_label = f"CAM {idx} ({role})" 
            c_chk = QCheckBox(c_label)
            c_chk.setChecked(True)
            c_chk.setCursor(Qt.CursorShape.PointingHandCursor)
            c_chk.toggled.connect(lambda checked, i=idx: self.toggle_cam(i, checked))
            if not cam_ok:
                c_chk.setEnabled(False)
                c_chk.setText(f"{c_label} (Missing)")
                c_chk.setChecked(False)
            
            self.cam_checks[idx] = c_chk
            
            # Mic Checkbox
            m_label = f"MIC {idx}"
            # short_mic_name = (mic_name[:15] + '..') if len(mic_name) > 15 else mic_name
            # m_chk = QCheckBox(f"{m_label} \n{short_mic_name}")
            m_chk = QCheckBox(m_label)
            m_chk.setToolTip(mic_name) # Show full name on hover
            
            m_chk.setChecked(True)
            m_chk.setCursor(Qt.CursorShape.PointingHandCursor)
            m_chk.toggled.connect(lambda checked, i=idx: self.toggle_mic(i, checked))
            if not mic_ok:
                 m_chk.setEnabled(False)
                 m_chk.setText(f"{m_label} (Missing)")
                 m_chk.setChecked(False)

            self.mic_checks[idx] = m_chk
            
            row.addWidget(c_chk)
            row.addWidget(m_chk)
            dev_layout.addLayout(row)
            
        dev_group.setLayout(dev_layout)
        self.layout.addWidget(dev_group)
        
        # --- Section 3: Tuning ---
        tune_group = QGroupBox("Performance Tuning")
        tune_layout = QVBoxLayout()
        tune_layout.setSpacing(15)
        tune_layout.setContentsMargins(15, 25, 15, 15)
        
        sliders = [
            ("Min Shot Duration", "min_shot_duration", 10, 100, 10.0, "s"),
            ("Audio Sensitivity", "audio_threshold", 1, 100, 100.0, ""), # Display raw or inv?
            ("Silence Hold Time", "silence_hold", 1, 50, 10.0, "s"),
            ("Face Loss Grace", "grace_period", 0, 50, 10.0, "s"),
        ]
        
        self.slider_labels = {}
        
        for name, attr, min_val, max_val, scale, unit in sliders:
            sl_container = QWidget()
            sl_layout = QVBoxLayout(sl_container)
            sl_layout.setContentsMargins(0,0,0,0)
            sl_layout.setSpacing(5)
            
            # Header Row
            top_row = QHBoxLayout()
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("font-weight: bold; color: #b0bec5;")
            
            curr_val = getattr(self.state, attr)
            val_lbl = QLabel(f"{curr_val:.2f}{unit}")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            val_lbl.setStyleSheet("color: #00bcd4; font-weight: bold;") 
            
            self.slider_labels[attr] = (val_lbl, unit)
            
            top_row.addWidget(name_lbl)
            top_row.addWidget(val_lbl)
            sl_layout.addLayout(top_row)
            
            # Slider
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setMinimum(min_val)
            sl.setMaximum(max_val)
            sl.setCursor(Qt.CursorShape.PointingHandCursor)
            
            if scale:
                pos = int(curr_val * scale)
            else:
                pos = int(curr_val)
            sl.setValue(pos)
            
            sl.valueChanged.connect(lambda val, a=attr, s=scale: self.update_param(a, val, s))
            
            sl_layout.addWidget(sl)
            tune_layout.addWidget(sl_container)
            
        tune_group.setLayout(tune_layout)
        self.layout.addWidget(tune_group)

        # --- Section 4: Recordings Manager ---
        rec_group = QGroupBox("Recordings")
        rec_layout = QVBoxLayout()
        rec_layout.setContentsMargins(15, 25, 15, 15)
        
        self.rec_list_layout = QVBoxLayout()
        rec_list_container = QWidget()
        rec_list_container.setLayout(self.rec_list_layout)
        
        # Helper text
        rec_layout.addWidget(QLabel("Click to Watch:"))
        rec_layout.addWidget(rec_list_container)
        
        btn_refresh = QPushButton("Refresh List")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_recordings)
        rec_layout.addWidget(btn_refresh)
        
        rec_group.setLayout(rec_layout)
        self.layout.addWidget(rec_group)
        
        # Initial Refresh
        self.refresh_recordings()

        # --- Section 5: Visuals ---
        vis_group = QGroupBox("Visual Settings")
        vis_layout = QVBoxLayout()
        vis_layout.setContentsMargins(15, 25, 15, 15)
        
        face_box_chk = QCheckBox("Draw Face Boxes")
        face_box_chk.setChecked(self.state.show_face_boxes)
        face_box_chk.setCursor(Qt.CursorShape.PointingHandCursor)
        face_box_chk.toggled.connect(self.toggle_face_boxes)
        
        dev_mode_chk = QCheckBox("Developer Options (Overlays)")
        dev_mode_chk.setChecked(self.state.developer_mode)
        dev_mode_chk.setCursor(Qt.CursorShape.PointingHandCursor)
        dev_mode_chk.toggled.connect(self.toggle_dev_mode)
        
        vis_layout.addWidget(face_box_chk)
        vis_layout.addWidget(dev_mode_chk)
        
        vis_layout.addWidget(face_box_chk)
        vis_group.setLayout(vis_layout)
        self.layout.addWidget(vis_group)
        
        self.layout.addStretch()
        
        # Status Bar
        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #777; font-size: 12px; margin-left: 10px;")
        self.statusBar().addWidget(self.status)

    def start_engine(self):
        if self.state.running: return
        
        self.state.running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status.setText("Initializing Engine & Recording...")
        
        self.engine_thread = threading.Thread(target=self._run_engine)
        self.engine_thread.daemon = True
        self.engine_thread.start()
        
    def _run_engine(self):
        try:
            self.engine.initialize()
            # Pass our signal emitter as the callback
            self.engine.run(frame_callback=self.frame_update_signal.emit) 
            self.on_engine_stopped()
        except Exception as e:
            print(f"Engine Error: {e}")
            self.on_engine_stopped()

    def stop_engine(self):
        self.state.running = False
        self.status.setText("Stopping...")
        
    def on_engine_stopped(self):
        self.state.running = False
        # Note: In production PyQt, use signals for thread-safety. 
        # For this prototype, direct calls usually work if only enabling buttons.
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status.setText("Stopped")

    def toggle_cam(self, idx, checked):
        self.state.set_cam_enabled(idx, checked)
        
    def toggle_mic(self, idx, checked):
        self.state.set_mic_enabled(idx, checked)
        
    def update_param(self, attr, val, scale):
        real_val = val / scale if scale else val
        setattr(self.state, attr, real_val)
        
        lbl, unit = self.slider_labels[attr]
        lbl.setText(f"{real_val:.2f}{unit}")

    def toggle_face_boxes(self, checked):
        self.state.show_face_boxes = checked

    def toggle_dev_mode(self, checked):
        self.state.developer_mode = checked

    def refresh_recordings(self):
        """Scans output/ folder and updates the list"""
        # Clear existing
        while self.rec_list_layout.count():
            child = self.rec_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        output_dir = "output"
        if not os.path.exists(output_dir):
            self.rec_list_layout.addWidget(QLabel("No recordings found."))
            return

        files = sorted([f for f in os.listdir(output_dir) if f.endswith('.avi') or f.endswith('_report.txt')], reverse=True)
        if not files:
             self.rec_list_layout.addWidget(QLabel("No recordings found."))
             return
             
        for f in files:
            btn = QPushButton(f)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Differentiate style for reports
            if f.endswith('.txt'):
                btn.setStyleSheet("text-align: left; padding-left: 10px; background-color: #444; color: #aaa;")
            else:
                btn.setStyleSheet("text-align: left; padding-left: 10px; background-color: #333;")
            
            # Use default param to capture loop variable
            btn.clicked.connect(lambda checked, fname=f: self.open_recording(fname))
            self.rec_list_layout.addWidget(btn)
            
    def open_recording(self, filename):
        path = os.path.abspath(os.path.join("output", filename))
        if os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                # Fallback for other OS if needed, but user is on Windows
                subprocess.call(('xdg-open', path))
        else:
            print(f"File not found: {path}")

    @pyqtSlot(object)
    def update_image_slot(self, cv_frame):
        """Standard PyQt slot to update the video label from a numpy BGR array"""
        if cv_frame is None: return
        
        # Convert BGR (OpenCV) to RGB (Qt)
        qt_img_format = QImage.Format.Format_RGB888
        
        h, w, ch = cv_frame.shape
        bytes_per_line = ch * w
        
        # We need a copy if data is not contiguous, but usually is.
        # cvtColor handles copy implicitly or returns new array.
        rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, qt_img_format)
        
        # Scale to fit label?
        pixmap = QPixmap.fromImage(q_img)
        
        # Scaled contents
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        self.video_label.setPixmap(scaled_pixmap)
import cv2 # Late import for the slot usage

def run_app():
    # High DPI Scaling
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
         QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
         QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Good base for dark theme
    
    state = AppState()
    engine = DirectorEngine(state)
    
    window = ControlPanel(state, engine)
    window.show()
    
    sys.exit(app.exec())
