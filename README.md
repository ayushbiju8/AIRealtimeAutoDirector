# 🎬 AutoDirector
**Intelligent AI Camera Switcher & Director**

AutoDirector is an automated video production system that acts as a real-time virtual director. It connects multiple cameras and microphones, detects who is speaking, tracks their faces, and intelligently switches the video feed to focus on the active speaker—just like a TV broadcast.

## ✨ Features

- **🤖 AI Director Engine**:
  - Automatically decides which camera to show.
  - **Speech Priority**: Cuts to the person speaking immediately.
  - **Anti-Flicker**: Enforces minimum shot durations to prevent jarring rapid cuts.
  - **Reaction Shots**: Switches to listeners during silence to maintain engagement.
  - **Staleness Checks**: Rotates views if a shot lingers too long.

- **🎥 Multi-Camera & Auto-Zoom**:
  - Supports multiple video inputs (Webcams, DroidCam, OBS Virtual Cam).
  - **Smooth Tracking**: Automatically zooms and pans to center the speaker's face.
  - **Cinematic Transitions**: Uses Linear Interpolation (LERP) for smooth camera movements.

- **🎙️ Advanced Audio Tracking (VAD)**:
  - **Per-Camera Audio**: Associates specific microphones with specific cameras (e.g., Laptop Mic -> Host, Phone Mic -> Guest).
  - Detects voice activity stats to drive switching logic.

- **💾 Session Recording & Analysis**:
  - **Director's Cut**: Automatically saves the final output stream to `output/recording_TIMESTAMP.avi`.
  - **Session Reports**: Generates a rich text summary (`_report.txt`) detailing speaking percentages, dominant emotions, and participant presence.

- **🎛️ Control Panel GUI**:
  - Modern Dark Theme interface built with **PyQt6**.
  - Real-time parameter tuning (Sensitivity, Reaction Time, etc.).
  - Visual Feedback for face detection and audio levels.
  - Built-in **Recordings Manager** to replay sessions.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/AutoDirector.git
    cd AutoDirector
    ```

2.  **Install Dependencies**:
    You need Python installed. Then run:
    ```bash
    pip install opencv-python numpy sounddevice PyQt6
    ```
    *(Note: You might need PortAudio installed on your system for `sounddevice`)*

3.  **Download Face Detection Model**:
    Ensure `visionai/face_detection_yunet_2023mar.onnx` is present in the correct folder (code expects it relative to the script).

## ⚙️ Configuration

Open `engine.py` (inside the `DirectorEngine` class) to configure your setup in the `CAMERA_CONFIG` section:

```python
self.CAMERA_CONFIG = {
    0: {
        "role": "HOST", 
        "mic_patterns": ["Realtek", "Array", "Intel"]   # Keywords for Laptop Mic
    },
    1: {
        "role": "GUEST", 
        "mic_patterns": ["DroidCam", "Virtual"]         # Keywords for Mobile/External Mic
    }
}
```

- **Keys (0, 1)**: The Camera Index (Standard OpenCV camera ID).
- **role**: Display name for the HUD (e.g., HOST, GUEST).
- **mic_patterns**: List of keywords to identify the correct microphone for this camera. The system scans available devices and picks the first match (prioritizing MME drivers on Windows).

## 🚀 Usage

Run the main script to launch the Control Panel:
```bash
python main.py
```

### Controls (GUI)
- **Start**: Initializes the AI Engine and begins recording.
- **Stop**: Stops the session and saves the video/report.
- **Tuning Sliders**: Adjust AI behavior in real-time.
- **Recordings**: Click any file in the "Recordings" list to open it.

## 📁 Project Structure

- **`main.py`**: Entry point. Launches the `gui_app`.
- **`gui_app.py`**: The PyQt6 Control Panel interface.
- **`engine.py`**: The backend coordinator. Handles device scanning, recording, and the main loop.
- **`fusion/director.py`**: The "Brain". Contains the logic for switching decisions.
- **`visionai/`**: Face Detection & Emotion Analysis.
- **`audioai/`**: Voice Activity Detection.
- **`capture/`**: Helper classes for Camera and Audio input.

