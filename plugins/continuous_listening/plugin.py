#!/usr/bin/env python3
"""Continuous listening plugin for VISUAL - background microphone capture with wake word detection"""
import threading, time, os, re, json
import builtins


def _g(name, default=None):
    """Lazily fetch a VISUAL helper: first from exec globals (visual.py), then builtins (tests)."""
    g = globals()
    if name in g and g[name] is not None:
        return g[name]
    return getattr(builtins, name, default)


def _cfg():
    return _g("CFG", {}) or {}


def _stop_file():
    return _g("STOP_FILE", os.path.join(os.path.expanduser("~/.visual"), "STOP"))


def _norm(s):
    fn = _g("_norm")
    if fn:
        return fn(s)
    return re.sub(r"[^\w\s]", " ", s.lower())


def _sh(cmd, timeout=10):
    fn = _g("sh")
    if fn:
        return fn(cmd, timeout)
    return ""


def _speak(text, wait=False):
    fn = _g("speak")
    if fn:
        try:
            return fn(text, wait=wait)
        except TypeError:
            return fn(text)
    return None


WAKE_WORDS = ["visual", "vishal", "विज़ुअल", "विजुअल", "विशाल"]
STOP_PHRASES = ["band ho jao", "band ho ja", "so jao", "shut down", "बंद हो जाओ", "बंद हो जा", "सो जाओ"]


class ContinuousListener:
    """Handles background listening with wake word detection"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.wakelock_acquired = False
        self.audio_chunk_duration = 2  # seconds
        self.max_fails = 40

    def start(self):
        """Start continuous listening foreground service"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        _speak("Continuous listening started, main screen band kar do")
        cfg = _cfg()
        try:
            _sh([
                "termux-notification", "--id", "visual_cl",
                "--ongoing", "--priority", "high",
                "--title", str(cfg.get("assistant_name", "VISUAL")) + " sun raha hai",
                "--content", "'" + str(cfg.get("owner_name", "Arjun")) + "' bolo ya Band dabao",
                "--button1", "Band", "--button1-action", "touch " + _stop_file(),
            ], 5)
        except Exception:
            pass

    def stop(self):
        """Graceful stop"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=8)
        sf = _stop_file()
        if os.path.exists(sf):
            try:
                os.remove(sf)
            except Exception:
                pass
        try:
            _sh(["termux-wake-unlock"])
        except Exception:
            pass
        try:
            _sh(["termux-notification-remove", "visual_cl"], 5)
        except Exception:
            pass
        _speak("Band ho raha hoon. Phir milte hain.")

    def _listen_loop(self):
        """Main audio capture and processing loop"""
        try:
            _sh(["termux-wake-lock"])
            self.wakelock_acquired = True
        except Exception:
            pass

        os.makedirs("shots", exist_ok=True)
        fails = 0

        while self.running:
            if os.path.exists(_stop_file()):
                break

            chunk_path = os.path.join("shots", "mic_chunk_%d.m4a" % int(time.time() * 1000))
            try:
                _sh(["termux-microphone-record", "-f", chunk_path,
                     "-l", str(self.audio_chunk_duration), "-e", "aac"], 10)
                time.sleep(0.5)

                if not os.path.exists(chunk_path):
                    fails += 1
                    time.sleep(0.3)
                    if fails > self.max_fails:
                        break
                    continue

                if os.path.getsize(chunk_path) < 500:
                    fails += 1
                    if fails > self.max_fails:
                        _speak("Sunne mein problem ho rahi hai. Band ho raha hoon.")
                        break
                    time.sleep(0.3)
                    continue

                fails = 0
                heard = self._check_audio(chunk_path)
                if heard:
                    self._handle_detected(heard, chunk_path)
                else:
                    time.sleep(0.2)
            except Exception as e:
                print("Listen loop error:", e)
                fails += 1
                time.sleep(1)
                if fails > self.max_fails:
                    break

        try:
            _sh(["termux-wake-unlock"])
            self.wakelock_acquired = False
        except Exception:
            pass

        sf = _stop_file()
        if os.path.exists(sf):
            try:
                os.remove(sf)
            except Exception:
                pass
        try:
            _sh(["termux-notification-remove", "visual_cl"], 3)
        except Exception:
            pass
        _speak("Listening stopped.")

    def _check_audio(self, audio_path):
        """Check audio for wake word or commands"""
        heard = ""
        try:
            import soundfile as sf
            import numpy as np
            data, sr = sf.read(audio_path, dtype="float32")
            if len(data) > 0:
                rms = float(np.sqrt(np.mean(data ** 2)))
                if rms > 0.01:
                    if (_cfg().get("keys", {}) or {}).get("groq"):
                        heard = self._quick_groq_transcribe(audio_path)
        except ImportError:
            pass
        except Exception as e:
            print("Audio check error:", e)
        return heard.strip() if heard else ""

    def _quick_groq_transcribe(self, audio_path):
        """Quick Groq Whisper transcription for short audio chunk"""
        key = (_cfg().get("keys", {}) or {}).get("groq")
        if not key:
            return ""
        try:
            import urllib.request
            bnd = "----visual" + str(int(time.time() * 1000))
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            parts = []
            for k, v in (("model", "whisper-large-v3-turbo"), ("language", "hi"), ("response_format", "json")):
                parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (bnd, k, v)).encode())
            parts.append(('--%s\r\nContent-Disposition: form-data; name="file"; filename="q.m4a"\r\nContent-Type: audio/mp4\r\n\r\n' % bnd).encode()
                         + audio_data + ("\r\n--%s--\r\n" % bnd).encode())
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                data=b"".join(parts),
                headers={"Authorization": "Bearer " + key,
                         "Content-Type": "multipart/form-data; boundary=" + bnd},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read()).get("text", "").strip()
        except Exception as e:
            print("Quick Groq transcribe error:", e)
            return ""

    def _handle_detected(self, heard, audio_path):
        """Process detected wake word or command"""
        normalized = _norm(heard)
        print("Detected:", heard)

        for phrase in STOP_PHRASES:
            if phrase in normalized:
                self.stop()
                return

        called = any(w in normalized for w in WAKE_WORDS)

        if called:
            cmd_text = normalized
            for w in WAKE_WORDS:
                cmd_text = cmd_text.replace(w, " ").strip()
            cmd_text = re.sub(r"\s+", " ", cmd_text).strip()

            if cmd_text:
                try:
                    chat = _g("chat")
                    if chat:
                        rep = chat("voice", cmd_text, voice=True)
                        _speak(rep, wait=True)
                except Exception as e:
                    print("Chat error:", e)
                    _speak("Samajh nahi aaya boss.")
            else:
                _speak("Haan boss? aap kya chahte hain?", wait=True)
        elif any(s in normalized for s in ["kaise ho", "kya hai", "kya kar rahe"]):
            _speak("Main sun raha hoon boss. Aap kya bolna chahte hain?", wait=True)


# Singleton instance
listener = ContinuousListener()


def cmd_continuous_listen():
    """Start continuous listening"""
    listener.start()


def cmd_continuous_stop():
    """Stop continuous listening"""
    listener.stop()


def init_plugin():
    """Plugin initialization"""
    pass