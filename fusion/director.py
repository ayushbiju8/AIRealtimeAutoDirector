import time
import random

class AutoDirector:
    def __init__(self, camera_config):
        self.camera_config = camera_config
        self.num_cameras = len(camera_config)
        # Map logical index 0..N to keys in config if needed, or assume keys correspond to indices
        # For simplicity, assuming keys are 0, 1, ...
        self.camera_indices = list(camera_config.keys())
        self.active_camera_index = self.camera_indices[0] if self.camera_indices else 0
        self.last_switch_time = time.time()
        
        # Configuration
        self.MIN_SHOT_DURATION = 4.0        # Minimum time to stay on one shot (prevent flicker)
        self.MAX_SHOT_DURATION = 15.0       # Maximum time before considering a switch (prevent boredom)
        self.REACTION_THRESHOLD = 2.0       # Time of silence before considering a reaction shot
        
        self.silence_start_time = None

    def update(self, speaking_map, faces_map):
        """
        Decides which camera should be active.
        
        Args:
            speaking_map (dict): Map of cam_index -> bool (is_speaking).
            faces_map (dict): Map of cam_index -> list of faces.
        """
        current_time = time.time()
        time_since_switch = current_time - self.last_switch_time
        
        # Determine global speaking state (is ANYONE speaking?)
        is_anyone_speaking = any(speaking_map.values())
        
        # Track silence duration
        if not is_anyone_speaking:
            if self.silence_start_time is None:
                self.silence_start_time = current_time
        else:
            self.silence_start_time = None
            
        silence_duration = (current_time - self.silence_start_time) if self.silence_start_time else 0.0
        
        # --- Rule 1: Anti-Flicker (Minimum Shot Duration) ---
        current_has_face = self._has_face(faces_map, self.active_camera_index)
        
        # Special Case: logic override if active cam has NO face but someone else does
        # (covered below)
        
        # --- Rule 2: Speaker Priority ---
        # Identify who is speaking
        speakers = [idx for idx, speaking in speaking_map.items() if speaking]
        
        if speakers:
            # Someone is speaking.
            
            # If the current active camera IS one of the speakers (and has face), stay.
            if self.active_camera_index in speakers and current_has_face:
                 # Check staleness?
                 if time_since_switch > self.MAX_SHOT_DURATION:
                     # If there are OTHER speakers, switch to them?
                     other_speakers = [s for s in speakers if s != self.active_camera_index]
                     if other_speakers:
                          # Switch to another speaker if they have a face
                          for s in other_speakers:
                              if self._has_face(faces_map, s):
                                  self._switch_to(s)
                                  return self.active_camera_index
                     
                     # Else maybe switch to reaction shot? No, keep focus on speaker.
                 return self.active_camera_index
            
            # Check if we should switch to a speaker
            if time_since_switch > self.MIN_SHOT_DURATION or not current_has_face:
                # Find a speaker who has a face
                # Prioritize: 
                # 1. A speaker with a face
                # 2. (Maybe) A speaker without a face? (Audio only? No, boring)
                
                # Check all speakers
                for s in speakers:
                     if self._has_face(faces_map, s):
                         self._switch_to(s)
                         return self.active_camera_index
        
        # --- Rule 3: Reaction / Pacing (Silence) ---
        if not is_anyone_speaking and silence_duration > self.REACTION_THRESHOLD:
            if time_since_switch > self.MIN_SHOT_DURATION:
                best_alt = self._find_best_alternative(faces_map, self.active_camera_index)
                if best_alt is not None:
                    self._switch_to(best_alt)
                    return self.active_camera_index

        # --- Rule 4: Staleness / No Face ---
        if not current_has_face:
             # Urgent switch needed
             best_alt = self._find_best_alternative(faces_map, self.active_camera_index)
             if best_alt is not None:
                 self._switch_to(best_alt)
        elif time_since_switch > self.MAX_SHOT_DURATION:
             best_alt = self._find_best_alternative(faces_map, self.active_camera_index)
             if best_alt is not None:
                 self._switch_to(best_alt)

        return self.active_camera_index

    def _switch_to(self, index):
        if index != self.active_camera_index:
            self.active_camera_index = index
            self.last_switch_time = time.time()
            role = self.camera_config.get(index, {}).get("role", "UNKNOWN")
            print(f"🎬 Director: CUT to Camera {index} ({role})")

    def _has_face(self, faces_map, index):
        faces = faces_map.get(index)
        return faces is not None and len(faces) > 0

    def _find_best_alternative(self, faces_map, exclude_index):
        # Candidates from configured indices
        candidates = [i for i in self.camera_indices if i != exclude_index]
        random.shuffle(candidates) # Diversity
        
        for i in candidates:
            if self._has_face(faces_map, i):
                return i
        return None
