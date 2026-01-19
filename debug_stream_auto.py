
import sounddevice as sd
import time

# Helper to find iQOO
def finds_iqoo():
    for i, dev in enumerate(sd.query_devices()):
        if "iQOO" in dev['name'] and dev['max_input_channels'] > 0:
            return i
    return None

idx = finds_iqoo()
if idx is None:
    print("iQOO not found")
    exit()

print(f"Testing Auto-Param on Device {idx}")

def cb(indata, frames, time, status):
    if status: print(status)

try:
    # Try with MINIMAL arguments. Let PortAudio figure it out.
    with sd.InputStream(device=idx, channels=1, callback=cb): 
        print("SUCCESS with Auto Params!")
        time.sleep(1.5)
except Exception as e:
    print(f"FAILED with Auto: {e}")

try:
    # Try with 8000 but NO blocksize
    print("Testing 8000Hz, No Blocksize")
    with sd.InputStream(device=idx, samplerate=8000, channels=1, callback=cb):
        print("SUCCESS with 8000Hz!")
        time.sleep(1.5)
except Exception as e:
    print(f"FAILED with 8000Hz: {e}")
