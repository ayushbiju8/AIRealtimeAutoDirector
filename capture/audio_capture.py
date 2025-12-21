import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.03  

def audio_callback(indata, frames, time, status):
    volume = np.linalg.norm(indata)
    print(f"Volume: {volume:.4f}")

with sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
    callback=audio_callback
):
    print("🎙️ Listening... Press Ctrl+C to stop")
    while True:
        pass
