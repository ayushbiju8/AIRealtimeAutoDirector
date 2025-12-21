import cv2
import numpy as np
from capture.camera import Camera
from visionai.face_detect import FaceDetector
from audioai.vad import VoiceActivityDetector
from fusion.director import AutoDirector

def main():
    try:
        # Camera Configuration
        CAMERA_CONFIG = {
            0: {"role": "HOST", "mic_patterns": ["Realtek", "Array", "Intel"]},
            1: {"role": "GUEST", "mic_patterns": ["DroidCam", "Virtual"]},
            # Add more here if needed
        }
        
        # Initialize cameras
        active_cameras = {}
        valid_config = {}
        
        for idx in CAMERA_CONFIG.keys():
            try:
                c = Camera(idx)
                if c.cap.isOpened():
                    active_cameras[idx] = c
                    valid_config[idx] = CAMERA_CONFIG[idx]
                    print(f"Initialized Camera {idx} ({CAMERA_CONFIG[idx]['role']})")
                else:
                    print(f"Camera {idx} failed to open.")
            except Exception as e:
                print(f"Camera {idx} initialization error: {e}")

        if not active_cameras:
            print("No cameras found!")
            return
            
        director = AutoDirector(camera_config=valid_config)
        
        detector = FaceDetector()
        
        # Initialize Audio (VADs)
        import sounddevice as sd
        all_devices = sd.query_devices()
        vads = {} # cam_idx -> vad_instance
        
        for cam_idx in valid_config.keys():
            config = valid_config[cam_idx]
            patterns = config.get("mic_patterns", [])
            
            # Find matching mic
            mic_index = None
            mic_name = "Unknown"
            
            for i, dev in enumerate(all_devices):
                if dev['max_input_channels'] > 0:
                    dname = dev['name']
                    # Check if any pattern matches
                    if any(p in dname for p in patterns):
                        mic_index = i
                        mic_name = dname
                        break
            
            if mic_index is not None:
                print(f"Assigning Mic '{mic_name}' to Camera {cam_idx} ({config['role']})")
                try:
                    v = VoiceActivityDetector(device_index=mic_index)
                    v.start()
                    vads[cam_idx] = v
                except Exception as e:
                    print(f"Failed to start VAD for Camera {cam_idx}: {e}")
            else:
                print(f"No matching microphone found for Camera {cam_idx}")

        print("Starting AutoDirector. Press 'q' to quit.")
        
        frame_count = 0
        
        # Smooth Zoom & Pan parameters
        current_zoom = 1.0
        target_zoom = 1.0
        
        # Will be initialized on first frame
        current_cx, current_cy = None, None
        target_cx, target_cy = None, None
        
        MAX_ZOOM = 1.5
        SMOOTHING_FACTOR = 0.1
        
        while True:
            # 1. Capture from ALL cameras
            frames = {}
            for idx, cam in active_cameras.items():
                ret, frame = cam.read()
                if ret:
                    frames[idx] = frame
                else:
                    frames[idx] = None
            
            if not any(f is not None for f in frames.values()):
                print("Failed to grab any frames")
                break
                
            frame_count += 1
            
            # 2. Detect Faces on ALL valid frames
            if frame_count % 2 == 0:
                current_faces_map = {}
                for idx, frame in frames.items():
                    if frame is not None:
                        current_faces_map[idx] = detector.detect(frame)
                # Store for next iteration
                last_faces_map = current_faces_map
            else:
                 # Use last known faces
                 if 'last_faces_map' in locals():
                    current_faces_map = last_faces_map
                 else:
                    current_faces_map = {}
            
            # 3. Director Decision
            # Construct speaking map
            speaking_map = {}
            for idx in vads:
                speaking_map[idx] = vads[idx].is_speaking
                
            active_cam_idx = director.update(speaking_map, current_faces_map)
            
            # Ensure valid active camera
            if active_cam_idx not in frames or frames[active_cam_idx] is None:
                # Fallback to first available
                available = [k for k, v in frames.items() if v is not None]
                if available:
                    active_cam_idx = available[0]
                else:
                    break
            
            active_frame = frames[active_cam_idx]
            if active_frame is None:
                 continue

            # --- RENDERING (Zoom/Pan) for Active Frame ---
            orig_h, orig_w = active_frame.shape[:2]
            
            # Reset centers if camera changed (Director handles switching, we detect change?)
            # The director logic stores active_camera_index.
            # If we switched physically this frame:
            if 'last_active_cam_idx' not in locals():
                last_active_cam_idx = active_cam_idx
            
            if active_cam_idx != last_active_cam_idx:
                # Reset zoom/pan on switch
                current_zoom = 1.0
                target_zoom = 1.0
                current_cx = orig_w / 2
                current_cy = orig_h / 2
                target_cx = orig_w / 2
                target_cy = orig_h / 2
                last_active_cam_idx = active_cam_idx

            # Initialize centers if needed
            if current_cx is None:
                current_cx, current_cy = orig_w / 2, orig_h / 2
                target_cx, target_cy = orig_w / 2, orig_h / 2
            
            # Get faces for active camera
            faces = current_faces_map.get(active_cam_idx, None)
            
             # Determine Targets (Zoom if active cam speaker is speaking)
            active_vad = vads.get(active_cam_idx)
            is_active_speaking = active_vad.is_speaking if active_vad else False
            
            target_zoom = MAX_ZOOM if is_active_speaking else 1.0
            
            if is_active_speaking and faces is not None and len(faces) > 0:
                face = faces[0]
                x, y, w, h = face[:4]
                target_cx = x + w / 2
                target_cy = y + h / 2
            else:
                target_cx = orig_w / 2
                target_cy = orig_h / 2
            
            # Smooth Updates
            current_zoom += (target_zoom - current_zoom) * SMOOTHING_FACTOR
            current_cx += (target_cx - current_cx) * SMOOTHING_FACTOR
            current_cy += (target_cy - current_cy) * SMOOTHING_FACTOR
            
            # Calculate Crop
            crop_w = orig_w / current_zoom
            crop_h = orig_h / current_zoom
            
            x1 = max(0, min(current_cx - crop_w / 2, orig_w - crop_w))
            y1 = max(0, min(current_cy - crop_h / 2, orig_h - crop_h))
            x2 = x1 + crop_w
            y2 = y1 + crop_h
            
            # Crop and Resize
            ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
            if ix2 > ix1 and iy2 > iy1:
                display_frame = cv2.resize(active_frame[iy1:iy2, ix1:ix2], (orig_w, orig_h))
            else:
                display_frame = active_frame

            # Transform Face Coordinates
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
            
            # Draw
            detector.draw(display_frame, np.array(display_faces) if display_faces else None)
            
            # Overlays
            # FPS
            if active_cam_idx in active_cameras:
                active_cameras[active_cam_idx].draw_fps(display_frame)
            
            # Role Name
            role_config = CAMERA_CONFIG.get(active_cam_idx, {})
            role_name = role_config.get('role', f"CAM {active_cam_idx}")
            
            # Draw Audio Statuses for all cams
            y_offset = 60
            for vid, v in vads.items():
                status = "SPEAK" if v.is_speaking else "SILENT"
                clr = (0, 255, 0) if v.is_speaking else (0, 0, 255)
                rname = CAMERA_CONFIG.get(vid, {}).get('role', f"CAM {vid}")
                cv2.putText(display_frame, f"{rname}: {status}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, clr, 1)
                y_offset += 25
            
            cv2.putText(display_frame, f"{role_name} (CAM {active_cam_idx})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(display_frame, f"Zoom: {current_zoom:.2f}x", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
            
            cv2.imshow("AutoDirector", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                # Manual toggle (hacky)
                available_keys = list(active_cameras.keys())
                if len(available_keys) > 1:
                    current_pos = available_keys.index(active_cam_idx) if active_cam_idx in available_keys else 0
                    next_pos = (current_pos + 1) % len(available_keys)
                    new_idx = available_keys[next_pos]
                    director._switch_to(new_idx) 
                    current_zoom = 1.0 # Reset zoom
                    
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'active_cameras' in locals():
            for c in active_cameras.values():
                c.release()
        if 'vads' in locals():
            for v in vads.values():
                v.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
