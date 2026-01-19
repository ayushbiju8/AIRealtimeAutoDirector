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
        self.FACE_LOSS_THRESHOLD = 2.0      # Grace period for temporary face loss
        
        self.silence_start_time = None
        self.face_loss_start_time = None # Track when we lost face on active cam

    def update(self, speaking_map, faces_map, volume_map=None, emotions_map=None):
        """
        Decides which camera should be active.
        """
        # Resolve Dominant Speaker (Mic Bleed Handling)
        if volume_map:
            speaking_map = self._resolve_dominant_speakers(speaking_map, volume_map)

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
        
        # Track face loss
        if current_has_face:
            self.face_loss_start_time = None
        else:
            if self.face_loss_start_time is None:
                self.face_loss_start_time = current_time
        
        face_loss_duration = (current_time - self.face_loss_start_time) if self.face_loss_start_time else 0.0
        
        # Determine if we REALLY need to switch due to face loss (grace period exceeded)
        urgent_face_switch_needed = not current_has_face and face_loss_duration > self.FACE_LOSS_THRESHOLD
        
        # --- Rule 0: High Emotion Reaction Shot (NEW) ---
        # If someone else is showing a strong emotion (Surprise, Happy), cut to them!
        # But only if we aren't cutting away from an active speaker too fast (unless it's REALLY good)
        if emotions_map and time_since_switch > 2.0: # Allow faster cuts for reactions
            high_salience = ['Surprise', 'Happy', 'Fear']
            
            # Check other cameras
            for idx in self.camera_indices:
                if idx == self.active_camera_index: continue
                
                # Check emotion
                emo = emotions_map.get(idx)
                if emo in high_salience:
                    # Switch!
                    # But verify they have a face (implied by having an emotion, but good to check)
                     if self._has_face(faces_map, idx):
                        # print(f"😲 Reaction Shot to Cam {idx} due to {emo}!")
                        self._switch_to(idx)
                        return self.active_camera_index
        
        # --- Rule 2: Speaker Priority ---
        # Identify who is speaking
        speakers = [idx for idx, speaking in speaking_map.items() if speaking]
        
        if speakers:
            # Someone is speaking.
            
            # If the current active camera IS one of the speakers (and has face OR within grace period), stay.
            # We treat "within grace period" as "effectively has face" for retention purposes
            if self.active_camera_index in speakers and not urgent_face_switch_needed:
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
            # Only switch if we are allowed to (min duration passed) OR if we URGENTLY need to (face lost)
            if time_since_switch > self.MIN_SHOT_DURATION or urgent_face_switch_needed:
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
        if urgent_face_switch_needed:
             # Urgent switch needed because face is definitively gone
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

    def _resolve_dominant_speakers(self, speaking_map, volume_map):
        """
        If multiple people are 'speaking' (according to VAD), but one is significantly louder,
        assume the others are just bleed/crosstalk and mute them in the map.
        """
        # Identify who is currently marked as speaking
        speakers = [idx for idx, is_speaking in speaking_map.items() if is_speaking]
        
        if len(speakers) <= 1:
            return speaking_map
            
        # Compare volumes
        # Find the loudest speaker
        max_vol = -1.0
        loudest_idx = None
        
        for idx in speakers:
            vol = volume_map.get(idx, 0.0)
            if vol > max_vol:
                max_vol = vol
                loudest_idx = idx
        
        if loudest_idx is None:
            return speaking_map
            
        # Create a new map where only the loudest (or those close to it) remain
        # For strict dominance: only keep the loudest.
        # But maybe we want a margin? e.g. if volumes are very close (0.8 vs 0.79), keep both?
        # Let's try strict dominance for now to solve the bleed issue aggressively.
        
        new_speaking_map = speaking_map.copy()
        
        # DOMINANCE_RATIO = 0.5 # If a mic is < 50% of the max volume, drop it.
        # Actually, let's just pick the winner.
        
        for idx in speakers:
            if idx != loudest_idx:
                # If this speaker is significantly quieter than the max, mute them.
                # Let's say if they are less than 70% of the max volume.
                if volume_map.get(idx, 0.0) < (max_vol * 0.7):
                    new_speaking_map[idx] = False
                    # trigger print only occasionally or if state changed? 
                    # For now just silent logic.
                    
        return new_speaking_map
