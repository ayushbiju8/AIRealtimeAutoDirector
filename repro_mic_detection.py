
import sounddevice as sd

# Simulated Config from engine.py
CAMERA_CONFIG = {
    0: {"role": "HOST", "mic_patterns": ["Realtek", "Array", "Intel"]},
    1: {"role": "GUEST", "mic_patterns": ["DroidCam", "Virtual", "iQOO", "Hands-Free"]},
}

def scan_simulated():
    all_audio_devices = sd.query_devices()
    print(f"Found {len(all_audio_devices)} devices.")
    
    for idx, config in CAMERA_CONFIG.items():
        print(f"Checking Camera {idx} ({config['role']})...")
        mic_found = False
        mic_name = "Unknown"
        
        patterns = config.get("mic_patterns", [])
        print(f"  Looking for patterns: {patterns}")
        
        # Get Host APIs once
        host_apis = sd.query_hostapis()
        
        found = False
        for p in patterns:
            matches = []
            for i, dev in enumerate(all_audio_devices):
                if dev['max_input_channels'] > 0:
                    dname = dev['name']
                    # Check match
                    if p in dname:
                        matches.append((i, dev))
            
            # Priority 1: MME
            for i, dev in matches:
                api_name = host_apis[dev['hostapi']]['name']
                if "MME" in api_name:
                    mic_found = True
                    mic_name = dev['name']
                    print(f"  [MATCH] Found MME mic: {dname}")
                    found = True
                    break
            
            if found: break
            
            # Priority 2: Any
            if matches:
                 mic_found = True
                 mic_name = matches[0][1]['name']
                 print(f"  [MATCH] Found (non-MME) mic: {mic_name}")
                 found = True
                 break
        
        if not mic_found:
            print(f"  [FAIL] No mic found matching patterns.")

if __name__ == "__main__":
    scan_simulated()
