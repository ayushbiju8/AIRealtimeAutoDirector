import sounddevice as sd
import numpy as np
import threading

class VoiceActivityDetector:
    def __init__(
        self,
        sample_rate=16000,
        chunk_duration=0.03,
        speech_threshold=0.05,
        speech_frames_required=4,
        device_index=None
    ):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.speech_threshold = speech_threshold
        self.speech_frames_required = speech_frames_required
        self.device_index = device_index

        self.current_volume = 0.0
        self.speech_counter = 0
        self.is_speaking = False

        self.running = False
        self.stream = None

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status)

        volume = np.linalg.norm(indata)
        self.current_volume = volume

        if volume > self.speech_threshold:
            self.speech_counter += 1
        else:
            self.speech_counter = max(0, self.speech_counter - 1)

        self.is_speaking = self.speech_counter >= self.speech_frames_required

    def start(self):
        if self.running:
            return

        self.running = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            blocksize=int(self.sample_rate * self.chunk_duration),
            callback=self._audio_callback,
            device=self.device_index
        )
        self.stream.start()
        print(f"🎙️ Voice Activity Detection Started (Device: {self.device_index if self.device_index is not None else 'Default'})")

    def stop(self):
        if not self.running:
            return

        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        print("🎙️ Voice Activity Detection Stopped")

if __name__ == "__main__":
    import time
    vad = VoiceActivityDetector()
    vad.start()
    try:
        while True:
            if vad.is_speaking:
                print(f"🗣️ SPEAKING (Vol: {vad.current_volume:.4f})")
            else:
                print(f"🤫 SILENT (Vol: {vad.current_volume:.4f})")
            time.sleep(0.1)
    except KeyboardInterrupt:
        vad.stop()
