
import cv2
import numpy as np
import os

class EmotionDetector:
    def __init__(self, model_path=None):
        if model_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(current_dir, "emotion_ferplus.onnx")
        
        self.net = cv2.dnn.readNetFromONNX(model_path)
        self.emotions = ['Neutral', 'Happy', 'Surprise', 'Sad', 'Angry', 'Disgust', 'Fear', 'Contempt']

    def detect_emotion(self, frame, face_box):
        """
        frame: Full image
        face_box: [x, y, w, h] from face detector
        Returns: string (dominant emotion)
        """
        x, y, w, h = map(int, face_box)
        
        # Padding to capture full face
        h_img, w_img = frame.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        
        if w <= 0 or h <= 0:
            return "Unknown"
            
        face_img = frame[y:y+h, x:x+w]
        
        # Preprocessing for FERPlus
        # 1. Grayscale
        if len(face_img.shape) == 3:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_img
            
        # 2. Resize to 64x64
        resized = cv2.resize(gray, (64, 64))
        
        # 3. Blob (normalization)
        # FERPlus often expects 0-255 inputs or generic normalization
        # Let's try standard blobFromImage.
        blob = cv2.dnn.blobFromImage(resized, 1.0, (64, 64), (0, 0, 0), swapRB=False, crop=False)
        
        self.net.setInput(blob)
        scores = self.net.forward()
        
        # Softmax to get probabilities (optional, but argmax is enough)
        # scores is [1, 8]
        
        idx = np.argmax(scores[0])
        return self.emotions[idx]
