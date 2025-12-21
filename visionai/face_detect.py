import cv2
import numpy as np
import os

class FaceDetector:
    def __init__(self, model_path=None, score_threshold=0.6, nms_threshold=0.3):
        if model_path is None:
            # Default to the file in the same directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(current_dir, "face_detection_yunet_2023mar.onnx")
        
        self.detector = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=(320, 320),
            score_threshold=score_threshold,
            nms_threshold=nms_threshold,
            top_k=5000
        )
        self.input_size_set = False

    def detect(self, frame):
        h, w, _ = frame.shape
        # Input size needs to be set once or if dimensions change. 
        # For simplicity, we can set it if it hasn't been set, or always set it.
        # FaceDetectorYN requires input size to match the frame size.
        self.detector.setInputSize((w, h))
        
        _, faces = self.detector.detect(frame)
        return faces

    def draw(self, frame, faces):
        if faces is not None:
            for face in faces:
                x, y, w_box, h_box = map(int, face[:4])
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w_box, y + h_box),
                    (0, 255, 0),
                    2
                )
                # Draw landmarks if needed (eyes, nose, mouth) - optional
                # for i in range(5):
                #     k = 4 + 2 * i
                #     cv2.circle(frame, (int(face[k]), int(face[k+1])), 2, (0, 0, 255), -1)
        return frame
