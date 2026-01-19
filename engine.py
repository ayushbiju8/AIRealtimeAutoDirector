import cv2
import numpy as np
import time
import sounddevice as sd
import traceback
import os
from datetime import datetime

from capture.camera import Camera
from visionai.face_detect import FaceDetector
from visionai.emotion_detect import EmotionDetector
from audioai.vad import VoiceActivityDetector
from fusion.director import AutoDirector

class DirectorEngine:
    def __init__(self, state):
        self.state = state
        self.active_cameras = {}
        self.vads = {}
        self.detector = None
        self.emotion_detector = None
        self.director = None
        
        # Config
        self.CAMERA_CONFIG = {
            0: {"role": "HOST", "mic_patterns": ["Realtek", "Array", "Intel"]},
            1: {"role": "GUEST", "mic_patterns": ["DroidCam", "Virtual", "Input"]},
            # Add more here if needed
        }

    def initialize(self):
        # We don't initialize here anymore if we want to scan first.
        # But 'initialize' is called by the thread.
        # We need a separate 'scan' method called by UI before showing window.
        pass

    def scan_devices(self):
        """
        Checks which devices are actually connected by scanning indices 0-3.
        Merges with config if available, otherwise creates default entry.
        Returns a dict of available indices and their metadata.
        """
        available = {}
        print("Scanning devices...")
        
        # Audio Devices Scan
        all_audio_devices = sd.query_devices()
        host_apis = sd.query_hostapis()

        print("\n--- DEBUG: All Detected Audio Devices ---")
        for i, d in enumerate(all_audio_devices):
            if d['max_input_channels'] > 0:
                print(f"[{i}] {d['name']} (API: {host_apis[d['hostapi']]['name']})")
        print("------------------------------------------\n")

        
        # Scan range of camera indices (e.g., 0 to 3)
        for idx in range(4):
            # 1. Check Camera Availability
            cam_found = False
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    cam_found = True
                    cap.read() # Try reading a frame to be sure
                    cap.release()
            except:
                pass
            
            # 2. Check Microphone Availability (Only if config exists for this idx)
            mic_found = False
            mic_name = "Unknown"
            config = self.CAMERA_CONFIG.get(idx, {})
            
            if config:
                patterns = config.get("mic_patterns", [])
                
                # Search for Mic
                matches = []
                for i, dev in enumerate(all_audio_devices):
                    if dev['max_input_channels'] > 0:
                        # Check match
                        for p in patterns:
                            if p in dev['name']:
                                matches.append((i, dev))
                                break
                
                # Priority 1: MME
                for i, dev in matches:
                    try:
                        api_name = host_apis[dev['hostapi']]['name']
                        if "MME" in api_name:
                            mic_found = True
                            mic_name = dev['name']
                            break
                    except: pass
                
                # Priority 2: Any match
                if not mic_found and matches:
                    mic_found = True
                    mic_name = matches[0][1]['name']
            
            # 3. Add to available if EITHER is found
            # If no config, we only add if Camera is found (can't guess Mic)
            if cam_found or (config and mic_found):
                 role = config.get('role', f"Camera {idx}")
                 available[idx] = {
                     'role': role,
                     'cam_found': cam_found,
                     'mic_found': mic_found,
                     'mic_name': mic_name if mic_found else "Default/None"
                 }
                 
        return available

    def initialize(self):
        """Initializes cameras and VADs based on AppState configuration"""
        print("Initializing Engine...")
        
        # Initialize Face Detector
        if self.detector is None:
             self.detector = FaceDetector()
        
        # Initialize Emotion Detector
        if self.emotion_detector is None:
             try:
                self.emotion_detector = EmotionDetector()
             except Exception as e:
                print(f"Failed to init EmotionDetector: {e}")

        # Initialize Cameras
        # We only init cameras that are ENABLED in state (or init all and ignore them later?)
        # Better to init all available so we can toggle them live?
        # Let's init all defined in config.
        
        for idx in self.CAMERA_CONFIG.keys():
            if idx in self.active_cameras: continue # Already active
            
            try:
                c = Camera(idx)
                # Check directly if read works or isOpened
                if c.cap.isOpened():
                    self.active_cameras[idx] = c
                    print(f"Initialized Camera {idx} ({self.CAMERA_CONFIG[idx]['role']})")
                else:
                    print(f"Camera {idx} failed to open.")
            except Exception as e:
                print(f"Camera {idx} initialization error: {e}")

        # Initialize Director
        valid_config = {k: v for k, v in self.CAMERA_CONFIG.items() if k in self.active_cameras}
        if self.director is None:
             self.director = AutoDirector(camera_config=valid_config)
        
        # Initialize Audio (VADs)
        all_devices = sd.query_devices()
        
        for cam_idx in valid_config.keys():
            if cam_idx in self.vads: continue
            
            config = valid_config[cam_idx]
            patterns = config.get("mic_patterns", [])
            
            mic_index = None
            mic_name = "Unknown"
            
            host_apis = sd.query_hostapis()
            found = False
            for pattern in patterns:
                matches = []
                for i, dev in enumerate(all_devices):
                    if dev['max_input_channels'] > 0 and pattern in dev['name']:
                        matches.append((i, dev))
                
                # Priority 1: MME
                for i, dev in matches:
                    api_name = host_apis[dev['hostapi']]['name']
                    if "MME" in api_name:
                        mic_index = i
                        mic_name = dev['name']
                        found = True
                        break
                if found: break

                # Priority 2: Any match
                if matches:
                    mic_index = matches[0][0]
                    mic_name = matches[0][1]['name']
                    found = True
                    break
            
            if mic_index is not None:
                print(f"Assigning Mic '{mic_name}' to Camera {cam_idx} ({config['role']})")
                try:
                    # Get device sample rate
                    dev_info = sd.query_devices(mic_index)
                    sr = int(dev_info.get('default_samplerate', 16000))
                    
                    # Initial params from state
                    v = VoiceActivityDetector(
                        device_index=mic_index, 
                        sample_rate=sr,
                        speech_threshold=self.state.audio_threshold,
                        silence_hold_time=self.state.silence_hold
                    )
                    v.start()
                    self.vads[cam_idx] = v
                    print(f"Started VAD for Camera {cam_idx} w/ Sample Rate {sr}Hz")
                except Exception as e:
                    print(f"Failed to start specific VAD for Camera {cam_idx}: {e}")
                    print(f"⚠️ Attempting fallback to System Default Microphone...")
                    try:
                        v = VoiceActivityDetector(
                            device_index=None, # Uses default
                            speech_threshold=self.state.audio_threshold,
                            silence_hold_time=self.state.silence_hold
                        )
                        v.start()
                        self.vads[cam_idx] = v
                        # Update role name to indicate fallback
                        self.CAMERA_CONFIG[cam_idx]['role'] += " (Def)"
                        print(f"✅ Fallback to Default Mic successful for Camera {cam_idx}")
                    except Exception as e2:
                        print(f"❌ Fallback failed: {e2}")
            else:
                print(f"No matching microphone found for Camera {cam_idx}")

    def run(self, frame_callback=None):
        """Main Processing Loop"""
        print("Starting Engine Loop...")
        frame_count = 0
        
        # Initialize Video Writer
        # Ensure output folder exists
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"recording_{timestamp}.avi")
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        # Typical webcam res is 640x480, verify active_cam resolution if possible or default
        TARGET_FPS = 15.0
        out = cv2.VideoWriter(filename, fourcc, TARGET_FPS, (640, 480))
        print(f"🎥 Recording started: {filename} (@ {TARGET_FPS} FPS)")
        
        # Smooth Zoom & Pan parameters
        current_zoom = 1.0
        target_zoom = 1.0
        current_cx, current_cy = None, None
        target_cx, target_cy = None, None
        
        MAX_ZOOM = 1.5
        SMOOTHING_FACTOR = 0.1
        
        # --- SESSION STATISTICS ---
        session_start = time.time()
        start_dt = datetime.now()
        
        # {cam_idx: total_speech_frames}
        speech_stats = {idx: 0 for idx in self.active_cameras}
        # {cam_idx: {emotion: count}}
        emotion_stats = {idx: {} for idx in self.active_cameras}
        # {cam_idx: {emotion: count}}
        emotion_stats = {idx: {} for idx in self.active_cameras}
        # {cam_idx: {count_val: frequency}} -> Histogram
        face_stats = {idx: {} for idx in self.active_cameras}
        
        print(f"📊 Stats tracking started for session: {start_dt}")
        
        print(f"📊 Stats tracking started for session: {start_dt}")
        
        last_loop_time = time.time()
        
        while self.state.running:
            loop_start = time.time()
            # Update dynamic parameters from State
            self.director.MIN_SHOT_DURATION = self.state.min_shot_duration
            self.director.FACE_LOSS_THRESHOLD = self.state.grace_period
            
            for vad in self.vads.values():
                vad.speech_threshold = self.state.audio_threshold
                vad.silence_hold_time = self.state.silence_hold
                
            # 1. Capture from ALL ENABLED cameras
            frames = {}
            for idx, cam in self.active_cameras.items():
                # Check if disabled in UI
                if not self.state.get_cam_enabled(idx):
                    frames[idx] = None
                    continue
                    
                ret, frame = cam.read()
                if ret:
                    frames[idx] = frame
                else:
                    frames[idx] = None
            
            # If no frames, wait a bit
            if not any(f is not None for f in frames.values()):
                time.sleep(0.1)
                continue
                
            frame_count += 1
            
            # 2. Detect Faces & Emotions on ALL valid frames
            if frame_count % 2 == 0:
                current_faces_map = {}
                current_emotions_map = {} # NEW: Track emotions for all cams
                
                for idx, frame in frames.items():
                    if frame is not None:
                        # Detect Faces
                        faces = self.detector.detect(frame)
                        current_faces_map[idx] = faces
                        
                        # Update Face Stats Histogram
                        if faces is not None:
                            count = len(faces)
                            # Initialize if needed (dynamic camera add?)
                            if idx not in face_stats: face_stats[idx] = {}
                            face_stats[idx][count] = face_stats[idx].get(count, 0) + 1
                        
                        # Detect Emotions (if faces found)
                        if self.emotion_detector and faces is not None and len(faces) > 0:
                            # Optimize: Only detect periodically
                            if frame_count % 6 == 0: 
                                emotion = self.emotion_detector.detect_emotion(frame, faces[0][:4])
                                current_emotions_map[idx] = emotion
                                
                                # Log Emotion Stat
                                if idx not in emotion_stats: emotion_stats[idx] = {}
                                emotion_stats[idx][emotion] = emotion_stats[idx].get(emotion, 0) + 1
                                
                                # Cache it for stability
                                if not hasattr(self, 'emotion_cache'): self.emotion_cache = {}
                                self.emotion_cache[idx] = emotion
                            else:
                                # Use cached value
                                if hasattr(self, 'emotion_cache'):
                                    current_emotions_map[idx] = self.emotion_cache.get(idx, "Neutral")

                last_faces_map = current_faces_map
                last_emotions_map = current_emotions_map
            else:
                 if 'last_faces_map' in locals():
                    current_faces_map = last_faces_map
                    current_emotions_map = last_emotions_map
                 else:
                    current_faces_map = {}
                    current_emotions_map = {}
            
            # 3. Director Decision
            speaking_map = {}
            volume_map = {}
            for idx in self.vads:
                # Check if mic disabled
                if not self.state.get_mic_enabled(idx):
                    speaking_map[idx] = False
                    volume_map[idx] = 0.0
                else:
                    speaking_map[idx] = self.vads[idx].is_speaking
                    volume_map[idx] = self.vads[idx].current_volume
                    
                    # Log Speech Stat
                    if speaking_map[idx]:
                        speech_stats[idx] = speech_stats.get(idx, 0) + 1
                
            active_cam_idx = self.director.update(speaking_map, current_faces_map, volume_map, current_emotions_map)
            
            # Ensure valid active camera (fallback if active is disabled or lost)
            if active_cam_idx not in frames or frames[active_cam_idx] is None:
                available = [k for k, v in frames.items() if v is not None]
                if available:
                    active_cam_idx = available[0]
                else:
                    # No cameras available
                    cv2.imshow("AutoDirector", np.zeros((480, 640, 3), dtype=np.uint8))
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.stop()
                    continue
            
            active_frame = frames[active_cam_idx]
            if active_frame is None: continue

            # --- RENDERING (Zoom/Pan) ---
            orig_h, orig_w = active_frame.shape[:2]
            
            if 'last_active_cam_idx' not in locals():
                last_active_cam_idx = active_cam_idx
            
            if active_cam_idx != last_active_cam_idx:
                current_zoom = 1.0
                target_zoom = 1.0
                current_cx = orig_w / 2
                current_cy = orig_h / 2
                target_cx = orig_w / 2
                target_cy = orig_h / 2
                last_active_cam_idx = active_cam_idx

            if current_cx is None:
                current_cx, current_cy = orig_w / 2, orig_h / 2
                target_cx, target_cy = orig_w / 2, orig_h / 2
            
            faces = current_faces_map.get(active_cam_idx, None)
            
            # Target Zoom logic
            active_vad = self.vads.get(active_cam_idx)
            is_active_speaking = active_vad.is_speaking if active_vad else False
            
            # Default Zoom
            target_zoom = 1.0 
            
            if is_active_speaking:
                # If speaking, zoom in a little (1.2)
                target_zoom = 1.2
                
                # If HIGH EMOTION, zoom in MORE (1.5)
                active_emotion = current_emotions_map.get(active_cam_idx, "Neutral")
                if active_emotion in ["Surprise", "Happy"]:
                    target_zoom = 1.5
            
            if is_active_speaking and faces is not None and len(faces) > 0:
                face = faces[0]
                x, y, w, h = face[:4]
                target_cx = x + w / 2
                target_cy = y + h / 2
            else:
                target_cx = orig_w / 2
                target_cy = orig_h / 2
            
            current_zoom += (target_zoom - current_zoom) * SMOOTHING_FACTOR
            current_cx += (target_cx - current_cx) * SMOOTHING_FACTOR
            current_cy += (target_cy - current_cy) * SMOOTHING_FACTOR
            
            crop_w = orig_w / current_zoom
            crop_h = orig_h / current_zoom
            
            x1 = max(0, min(current_cx - crop_w / 2, orig_w - crop_w))
            y1 = max(0, min(current_cy - crop_h / 2, orig_h - crop_h))
            x2 = x1 + crop_w
            y2 = y1 + crop_h
            
            ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
            if ix2 > ix1 and iy2 > iy1:
                display_frame = cv2.resize(active_frame[iy1:iy2, ix1:ix2], (orig_w, orig_h))
            else:
                display_frame = active_frame

            # Transform Face Coordinates for Drawing
            display_faces = []
            if faces is not None:
                scale_x = orig_w / (x2 - x1)
                scale_y = orig_h / (y2 - y1)
                for face in faces:
                    fx, fy, fw, fh = face[:4]
                    new_x = (fx - x1) * scale_x
                    new_y = (fy - y1) * scale_y
                    new_w = fw * scale_x
                    new_h = fh * scale_y
                    new_face = face.copy()
                    new_face[:4] = [new_x, new_y, new_w, new_h]
                    display_faces.append(new_face)
            
            # Draw Faces
            if self.state.show_face_boxes:
                self.detector.draw(display_frame, np.array(display_faces) if display_faces else None)
            
            # Overlays
            if self.state.developer_mode and active_cam_idx in self.active_cameras:
                self.active_cameras[active_cam_idx].draw_fps(display_frame)
            
            role_config = self.CAMERA_CONFIG.get(active_cam_idx, {})
            role_name = role_config.get('role', f"CAM {active_cam_idx}")
            
            if self.state.developer_mode:
                y_offset = 60
                for vid, v in self.vads.items():
                    if not self.state.get_mic_enabled(vid):
                        status = "DISABLED"
                        clr = (128, 128, 128)
                    else:
                        status = "SPEAK" if v.is_speaking else "SILENT"
                        clr = (0, 255, 0) if v.is_speaking else (0, 0, 255)
                        
                        # Volume Visualization
                        vol_pct = int((v.current_volume / 25.0) * 100) # Assuming max ~25
                        vol_pct = max(0, min(100, vol_pct))
                        
                    rname = self.CAMERA_CONFIG.get(vid, {}).get('role', f"CAM {vid}")
                    cv2.putText(display_frame, f"{rname}: {status} ({vol_pct}%)", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, clr, 1)
                    y_offset += 25
                
                
                cv2.putText(display_frame, f"{role_name} (CAM {active_cam_idx})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
                emotion_text = current_emotions_map.get(active_cam_idx, "Analyzing...")
                
                # Draw on Top Right
                text_size = cv2.getTextSize(emotion_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
                text_x = orig_w - text_size[0] - 20
                text_y = 40
                
                cv2.putText(display_frame, f"Emotion: {emotion_text}", (text_x - 120, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)

            # cv2.imshow("AutoDirector", display_frame)
            
            # Write to file
            if out.isOpened():
                out.write(display_frame)
            
            # Send to GUI
            if frame_callback:
                frame_callback(display_frame)
            
            # Key check requires cv2.waitKey if we want to intercept global keys, 
            # but without imshow waitKey might not work as expected for window events.
            # since we are headless (no opencv window), we rely on GUI stop button.
            
            # --- FPS LIMITING ---
            proc_time = time.time() - loop_start
            wait_time = (1.0 / TARGET_FPS) - proc_time
            if wait_time > 0:
                time.sleep(wait_time)
            
            # FPS Calculation (Smoothing)
            # real_fps = 1.0 / (time.time() - last_loop_time)
            # last_loop_time = time.time()
            # print(f"FPS: {real_fps:.1f}", end='\r')

        print("Engine Loop Stopped.")
        if out: out.release()
        
        # --- GENERATE SUMMARY REPORT ---
        try:
            report_file = filename.replace('.avi', '_report.txt')
            duration_sec = time.time() - session_start
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"AutoDirector Session Summary\n")
                f.write(f"==========================\n")
                f.write(f"Date: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration: {duration_sec:.2f} seconds\n\n")
                
                f.write(f"Participant Statistics\n")
                f.write(f"----------------------\n")
                
                for idx in self.active_cameras:
                    role = self.CAMERA_CONFIG.get(idx, {}).get('role', f"CAM {idx}")
                    f.write(f"\n[Camera {idx} - {role}]\n")
                    
                    # 1. Presence (Robust Max)
                    # Filter out counts that appeared in < 15 frames (approx 0.5-1s) to avoid glitches
                    f_hist = face_stats.get(idx, {})
                    valid_counts = [c for c, freq in f_hist.items() if freq > 15]
                    
                    if valid_counts:
                        robust_max = max(valid_counts)
                    else:
                        # Fallback to absolute max if nothing sustained (or 0)
                        robust_max = max(f_hist.keys()) if f_hist else 0
                        
                    f.write(f"  - Max Persons Detected: {robust_max}\n")
                    
                    # 2. Speaking
                    speech_frames = speech_stats.get(idx, 0)
                    # Approx duration (loop fps varies, but assuming ~15-20fps effective or using wall time would be better)
                    # Let's estimate % based on total frames
                    speech_pct = (speech_frames / max(1, frame_count)) * 100
                    f.write(f"  - Speaking Activity: {speech_pct:.1f}% of session\n")
                    
                    # 3. Emotions
                    f.write(f"  - Observed Emotions:\n")
                    e_counts = emotion_stats.get(idx, {})
                    if e_counts:
                        total_emotions = sum(e_counts.values())
                        # Sort by count
                        sorted_emotions = sorted(e_counts.items(), key=lambda x: x[1], reverse=True)
                        for emo, count in sorted_emotions:
                            pct = (count / total_emotions) * 100
                            f.write(f"    * {emo}: {pct:.1f}%\n")
                    else:
                        f.write(f"    * (None detected)\n")

            print(f"📄 Report generated: {report_file}")
            
        except Exception as e:
            print(f"❌ Failed to generate report: {e}")
            traceback.print_exc()

        self.cleanup()

    def stop(self):
        self.state.running = False
        
    def cleanup(self):
        print("Cleaning up resources...")
        try:
            for c in self.active_cameras.values():
                c.release()
            for v in self.vads.values():
                v.stop()
            cv2.destroyAllWindows()
            # Clear them so they can be re-inited if needed
            self.active_cameras = {}
            self.vads = {} 
        except Exception:
            pass
