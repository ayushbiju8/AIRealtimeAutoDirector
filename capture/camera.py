import cv2
import time
import threading

class Camera:
    def __init__(self, camera_id=0):
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {camera_id}")
        self.prev_time = 0
        
        # Threading setup
        self.stopped = False
        self.ret = False
        self.frame = None
        self.lock = threading.Lock()
        
        # Read first frame to ensure we have something
        self.ret, self.frame = self.cap.read()
            
        self.thread = threading.Thread(target=self._update, args=())
        self.thread.daemon = True
        self.thread.start()

    def _update(self):
        while True:
            if self.stopped:
                break
                
            ret, frame = self.cap.read()
            
            with self.lock:
                self.ret = ret
                self.frame = frame
            
            # Small sleep to yield CPU if camera is slow, 
            # though usually read() blocks so this might be redundant but safe.
            # time.sleep(0.001) 

    def read(self):
        with self.lock:
            # Return a copy to avoid threading race conditions if caller modifies it
            # actually copy might be expensive, let's just return reference 
            # as long as we don't write to it while reading.
            # But standard practice for robustness might be copy or just return.
            # For performance, returning reference is better.
            return self.ret, self.frame

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
        self.stopped = True
        if self.thread.is_alive():
            self.thread.join()
        self.cap.release()
