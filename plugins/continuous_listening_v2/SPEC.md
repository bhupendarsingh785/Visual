# Continuous Listening Upgrade Specification for VISUAL

## Goal
Make VISUAL truly continuously listen in background even when Android screen is off, wake word detection works, and responsive replies without draining battery excessively.

## Research Findings (from code analysis)
- Current `run_always()` uses `termux-wake-lock` to keep CPU running
- Uses `termux-speech-to-text` which is a blocking command
- Has wake word detection but relies on full speech recognition each loop iteration
- Notification with stop button works
- No true foreground service with microphone capture when screen off

## Architecture

### 1. Foreground Service Layer
- Create `continuous_listening.py` module with a long-running thread
- Use Android `foreground service` notification (ongoing priority) to indicate "listening"
- Hold `termux-wake-lock` continuously while listening
- Request `android.permission.RECORD_AUDIO` and handle runtime permissions

### 2. Wake Word Detection
- **Option A (Offline)**: Integrate Vosk speech-to-text with wake word model
  - Pros: Works offline, low latency, no internet needed
  - Cons: Requires model file download (~15-30MB)
  - Model: Porcupine (Picovoice) or Vosk wake word model
- **Option B (Online)**: Use Groq Whisper with short audio chunks
  - Pros: Good accuracy
  - Cons: Battery/data usage, privacy
- **Recommendation**: Start with Vosk wake word model (offline) for battery efficiency, fall back to Groq for full STT

### 3. Audio Capture Loop
- Use `termux-microphone-record` with short duration (1-2 seconds)
- VAD (Voice Activity Detection) to detect when user is speaking
- Buffer audio and send to STT engine only when voice detected
- Sleep 0.5s between chunks to save battery

### 4. Stop Conditions
- Wake word "visual"/"vishal" detected → wake up full mode
- Stop phrase "band ho jao" detected → graceful shutdown
- Notification stop button touch
- File `STOP` existence check (already implemented)

### 5. Battery Optimization
- Use `termux-wake-lock` strategically (not full CPU lock, just prevent screen timeout)
- Release wakelock when no audio detected for 30s
- Android Doze mode handling - foreground service should survive
- Limit to 80% CPU when idle

## Files to Create/Modify

### New File: `plugins/continuous_listening.py`
```python
"""
Continuous listening plugin for VISUAL
Handles background microphone capture, wake word detection, and responsive mode
"""
import threading, time, os, re
from ..cfg import CFG, MEMORY
from ..core import sh, speak, _norm, STOP_FILE

# Wake word models - offline option
# Could integrate: porcupine library or Vosk model

WAKE_WORDS = ["visual", "vishal", "विज़ुअल", "विजुअल", "विशाल"]
STOP_PHRASES = ["band ho jao", "band ho ja", "so jao"]

class ContinuousListener:
    def __init__(self):
        self.running = False
        self.thread = None
        self.wakelock = False
        
    def start(self):
        """Start the continuous listening foreground service"""
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        speak("Continuous listening started, main screen band kar do")
        
    def stop(self):
        """Graceful stop"""
        self.running = False
        if self.thread: self.thread.join(timeout=5)
        if os.path.exists(STOP_FILE): os.remove(STOP_FILE)
        try: sh(["termux-wake-unlock"]) 
        except: pass
        speak("Band ho raha hoon. Phir milte hain.")
        
    def _listen_loop(self):
        """Main audio capture and processing loop"""
        # Request microphone permission handling
        sh(["termux-wake-lock"])  # Keep CPU running
        
        # Show ongoing notification
        sh([
            "termux-notification", "--id", "visual_cl", 
            "--ongoing", "--priority", "high",
            "--title", "VISUAL sun raha hai",
            "--content", "'{CFG['assistant_name']} band ho jao' bolo ya Band dabao",
            "--button1", "Band", "--button1-action", f"touch {STOP_FILE}"
        ], 5)
        
        fails = 0
        while self.running:
            if os.path.exists(STOP_FILE): break
            
            # Record short audio chunk (2 seconds)
            p = os.path.join("shots", "mic_chunk.m4a")
            try:
                sh(["termux-microphone-record", "-f", p, "-l", "2", "-e", "aac"], 5)
                time.sleep(2.5)
                
                # Check audio size - if too small, continue
                if not os.path.exists(p) or os.path.getsize(p) < 1000:
                    fails += 1
                    if fails > 10: 
                        sh(["termux-wake-unlock"])
                        break
                    continue
                fails = 0
                
                # Check for wake word first (offline fast check)
                t = self._check_wake_word(p)
                
                if t:
                    # Wake word detected - full STT and respond
                    self._handle_wake_word(p)
                elif fails > 30:
                    # Too many fails, maybe stop
                    break
                    
            except Exception as e:
                print("Listen loop error:", e)
                time.sleep(1)
                
        # Cleanup
        try: sh(["termux-wake-unlock"])
        except: pass
        if os.path.exists(STOP_FILE): os.remove(STOP_FILE)
        try: sh(["termux-notification-remove", "visual_cl"], 5)
        except: pass
        
    def _check_wake_word(self, audio_path):
        """Quick wake word check - offline if possible"""
        # For now use quick audio check or Groq Whisper small model
        # Could integrate Vosk wake word here
        if not CFG.get("keys", {}).get("groq"): return ""
        # Short 2s clip to Groq Whisper
        return self._groq_quick_transcribe(audio_path)
        
    def _groq_quick_transcribe(self, path):
        """Quick Groq Whisper transcription of short audio"""
        # Similar to groq_transcribe but optimized for 2s clips
        key = CFG["keys"].get("groq")
        if not key: return ""
        # ... implement quick transcription
        return ""
        
    def _handle_wake_word(self, audio_path):
        """Full processing when wake word detected"""
        # Full STT, chat, reply
        # This switches to normal run_always mode
        pass

# Singleton instance
listener = ContinuousListener()

# CLI integration
def cmd_continuous_listen():
    """CLI: python visual.py continuous_listen"""
    listener.start()

def cmd_continuous_stop():
    """CLI: python visual.py continuous_stop"""
    listener.stop()
```

### Modified: `visual.py` `run_always()`
- Replace with call to plugin's start/stop
- Keep existing wake word/stop phrase logic as fallback
- Add plugin load at startup

### Configuration Updates
- New CFG option: `continuous_listen: true/false`
- `listen_engine`: add "continuous" option
- `wake_word_engine`: "offline"|"groq"|"vosk"
- `mic_chunk_duration`: seconds (default 2)

## Testing Plan
1. Start service: `python visual.py continuous_listen`
2. Screen off - should still hear wake word
3. Say "visual" → should respond
4. Say "band ho jao" → should stop
5. Notification stop button works
6. Battery test: check drain over 1 hour
7. Edge cases: phone call, other apps

## Success Criteria (SCORE >= 8)
- [ ] Wake word detected 80%+ times in quiet room within 3 attempts
- [ ] Stops on "band ho jao" 100% of tests
- [ ] Screen off doesn't prevent listening 95%+ tests
- [ ] Battery drain < 15% per hour (acceptable threshold)
- [ ] No crashes when switching between screen on/off
- [ ] Notification visible and functional during listening

## Next Steps
1. Create plugin skeleton
2. Integrate wake word detection (Vosk/Porcupine or Groq quick transcribe)
3. Test audio capture loop
4. Battery optimization
5. Final critic review and score improvement