
import sounddevice as sd
import numpy as np

# Find iQOO device index
target_idx = None
print("Scanning for iQOO...")
for i, dev in enumerate(sd.query_devices()):
    if "iQOO" in dev['name'] and dev['max_input_channels'] > 0:
        target_idx = i
        print(f"Found iQOO at index {i}: {dev['name']}")
        print(f"  SR: {dev['default_samplerate']}, In: {dev['max_input_channels']}")
        break

if target_idx is None:
    print("iQOO device not found!")
    exit(1)

sr = 8000 # hardcoded based on previous findings, or use dev['default_samplerate']

configs = [
    {"name": "Current (Block 240)", "blocksize": 240, "latency": None},
    {"name": "No Blocksize", "blocksize": None, "latency": None},
    {"name": "Latency 'high'", "blocksize": None, "latency": 'high'},
    {"name": "Latency 0.1s", "blocksize": None, "latency": 0.1},
    {"name": "Latency 0.05s", "blocksize": 400, "latency": 0.05},
]

def callback(indata, frames, time, status):
    if status:
        print(status)

print(f"\nTesting Stream on Device {target_idx} @ {sr}Hz")
for cfg in configs:
    print(f"\n--- Testing: {cfg['name']} ---")
    try:
        kwargs = {
            'samplerate': sr,
            'channels': 1,
            'callback': callback,
            'device': target_idx
        }
        if cfg['blocksize']: kwargs['blocksize'] = cfg['blocksize']
        if cfg['latency']: kwargs['latency'] = cfg['latency']
        
        with sd.InputStream(**kwargs):
            print("  SUCCESS! Stream opened.")
            sd.sleep(1000) # Run for 1s
            print("  Stream ran ok.")
    except Exception as e:
        print(f"  FAILED: {e}")
