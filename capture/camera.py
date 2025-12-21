import cv2
import time

class Camera:
    def __init__(self, camera_id=0):
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {camera_id}")
        self.prev_time = 0

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return False, None
        return True, frame

    def draw_fps(self, frame):
        current_time = time.time()
        fps = 1 / (current_time - self.prev_time) if self.prev_time else 0
        self.prev_time = current_time
        timestamp_ms = int(time.time() * 1000)

        cv2.putText(
            frame,
            f"FPS: {int(fps)} Time: {timestamp_ms}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        return frame

    def release(self):
        self.cap.release()
