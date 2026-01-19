import threading

class AppState:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Flags
        self.running = False
        
        # Configuration
        self.camera_selection = {} # {idx: bool} - True if enabled
        self.mic_selection = {}    # {idx: bool} - True if enabled
        
        # Tuning Parameters
        self.min_shot_duration = 4.0
        self.max_shot_duration = 15.0
        self.audio_threshold = 0.1
        self.silence_hold = 0.8
        self.grace_period = 2.0
        
        # Visuals
        self.show_face_boxes = True
        self.developer_mode = True # Controls text overlays
        
    def get_cam_enabled(self, idx):
        with self.lock:
            return self.camera_selection.get(idx, True) # Default enable

    def set_cam_enabled(self, idx, val):
        with self.lock:
            self.camera_selection[idx] = val

    def get_mic_enabled(self, idx):
        with self.lock:
            return self.mic_selection.get(idx, True) # Default enable

    def set_mic_enabled(self, idx, val):
        with self.lock:
            self.mic_selection[idx] = val
