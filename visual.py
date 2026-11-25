#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VISUAL - Arjun ka apna AI agent (Android + Termux)
Dekhta hai (camera + phone screen), sunta hai, bolta hai, sochta hai,
phone chalata hai, web se juda hai, khud cheezein banata hai.

Sirf Python standard library. Chalao:
    python visual.py            -> HAMESHA CHALU: screen band par bhi sunta hai + web app + Telegram
    python visual.py app        -> sirf orb web app (Chrome mein)
    python visual.py stop       -> band karo (ya bolo "VISUAL band ho jao")
    python visual.py chat       -> typing wala mode
    python visual.py adb        -> screen control (wireless debugging) jodo
    python visual.py setup      -> API key / naam set karo
"""
import base64, datetime, html, json, os, re, shutil, subprocess, sys, threading, time
import urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP = "VISUAL"
VERSION = "3.6 ENGINEER"
HOME = os.path.expanduser("~/.visual")
CONF = os.path.join(HOME, "config.json")
MEM = os.path.join(HOME, "memory.json")
CREATIONS = os.path.join(HOME, "creations")
SHOTS = os.path.join(HOME, "shots")
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(CREATIONS, exist_ok=True); os.makedirs(SHOTS, exist_ok=True)

PROVIDERS = {
    "gemini":     {"base": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.5-flash", "vision": True},
    "groq":       {"base": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile", "vision": False},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "model": "openrouter/free", "vision": True},
    # optional: aur free dimaag (key ho to cross-check mein judte hain)
    "mistral":    {"base": "https://api.mistral.ai/v1", "model": "mistral-small-latest", "vision": False},
    "cerebras":   {"base": "https://api.cerebras.ai/v1", "model": "llama-3.3-70b", "vision": False},
}

DEFAULT_CONF = {
    "assistant_name": APP,
    "owner_name": "Arjun",
    "language": "hi-IN",
    "keys": {"gemini": "", "groq": "", "openrouter": "", "mistral": "", "cerebras": ""},
    "models": {},                 # jaise {"gemini": "gemini-2.5-flash"} badalna ho to
    "provider_order": ["gemini", "openrouter", "groq", "mistral", "cerebras"],
    "web_host": "127.0.0.1", "web_port": 8765, "web_pin": "",
    "telegram_token": "", "telegram_owner_ids": [], "telegram_guest_chat": True,
    "adb_target": "",            # jaise "localhost:37123" (python visual.py adb)
    "speak_replies": True,
    "voice": "hi-IN-MadhurNeural",   # aadmi ki awaaz; aurat: hi-IN-SwaraNeural
    "neural_voice": True,
    "live_mode": True,              # Gemini Live: real-time awaaz (videos jaisa tez)
    "live_voice": "Charon",         # Live ki awaaz: Charon, Puck, Kore, Fenrir, Aoede...
    "confirm_risky": True,
    # hamesha sunne wala mode (visual always)
    "listen_engine": "android",   # "android" = termux-speech-to-text, "groq" = mic record + Groq Whisper
    "wake_word_required": True,    # naam bolne par hi kaam (TV/doosron ki baat par nahi)
    "wake_words": ["visual", "vishal", "विज़ुअल", "विजुअल", "विशाल"],
    "followup_seconds": 40,        # naam ke baad itni der bina naam ke bhi baat
    "stop_phrases": ["band ho jao", "band ho ja", "so jao", "shut down", "बंद हो जाओ", "बंद हो जा", "सो जाओ"],
}

# ---------------------------------------------------------------- config / memory
_lock = threading.RLock()

def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(default, dict):
            for k, v in default.items():
                d.setdefault(k, v)
        return d
    except Exception:
        return json.loads(json.dumps(default))

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

CFG = load_json(CONF, DEFAULT_CONF)
for _k in DEFAULT_CONF["keys"]: CFG["keys"].setdefault(_k, "")
for _p in DEFAULT_CONF["provider_order"]:
    if _p not in CFG.get("provider_order", []): CFG.setdefault("provider_order", []).append(_p)
for _p in PROVIDERS:
    k = os.environ.get(_p.upper() + "_API_KEY")
    if k: CFG["keys"][_p] = k
MEMORY = load_json(MEM, {"facts": [], "reminders": [], "sessions": {}})

def save_mem():
    with _lock: save_json(MEM, MEMORY)

# ---------------------------------------------------------------- helpers
def sh(cmd, timeout=40, inp=None):
    """Command chalao, output text lautao."""
    try:
        r = subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=timeout,
                           shell=isinstance(cmd, str))
        out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr.strip() else "")
        return out.strip() or ("ok" if r.returncode == 0 else f"error code {r.returncode}")
    except FileNotFoundError:
        return "ERROR: command nahi mila. Termux mein chalao: pkg install termux-api (aur Play/F-Droid se Termux:API app)."
    except subprocess.TimeoutExpired:
        return "ERROR: time khatam (timeout)."
    except Exception as e:
        return f"ERROR: {e}"

def has(cmd): return shutil.which(cmd) is not None

def http(url, data=None, headers=None, timeout=60):
    h = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) VISUAL/1.0"}
    h.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode(); h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def strip_html(s):
    s = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def speak(text, wait=False):
    if not CFG.get("speak_replies"): return
    mp3 = neural_tts(text) if CFG.get("neural_voice", True) else None
    if mp3 and has("termux-media-player"):
        f = os.path.join(TTS_DIR, "now.mp3")
        with open(f, "wb") as fh: fh.write(mp3)
        sh(["termux-media-player", "play", f], 10)
        if wait:
            time.sleep(1)
            for _ in range(240):
                st = sh(["termux-media-player", "info"], 5)
                if "Playing" not in st: break
                time.sleep(0.5)
        return
    if not has("termux-tts-speak"): return
    t = re.sub(r"https?://\S+", "link", re.sub(r"[*_#`>]", "", text))[:600]
    cmd = ["termux-tts-speak", "-l", "hi", "-r", "1.05", t]
    if wait: sh(cmd, 180)      # bolte waqt mic band rahe, taaki apni hi aawaz na sune
    else: threading.Thread(target=sh, args=(cmd, 180), daemon=True).start()

def adb(*args, timeout=30, binary=False):
    t = CFG.get("adb_target")
    if not has("adb"): return "ERROR: adb nahi hai. Chalao: pkg install android-tools"
    if not t: return "ERROR: screen control juda nahi. Chalao: python visual.py adb"
    cmd = ["adb", "-s", t] + list(args)
    if binary:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout
    out = sh(cmd, timeout)
    if "not found" in out or "offline" in out:
        sh(["adb", "connect", t], 15); out = sh(cmd, timeout)
    return out

# ---------------------------------------------------------------- images (vision)
_screen_scale = {"sx": 1.0, "sy": 1.0}

def image_to_dataurl(path, max_w=768):
    """Chhota JPEG banao (Pillow ho to), data URL lautao."""
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB"); w, h = im.size
        if w > max_w:
            im = im.resize((max_w, int(h * max_w / w)))
        sx, sy = w / im.size[0], h / im.size[1]
        out = path.rsplit(".", 1)[0] + "_small.jpg"; im.save(out, "JPEG", quality=70)
        with open(out, "rb") as f: b = f.read()
        return "data:image/jpeg;base64," + base64.b64encode(b).decode(), im.size, (sx, sy)
    except Exception:
        mime = "image/png" if path.endswith(".png") else "image/jpeg"
        with open(path, "rb") as f: b = f.read()
        return f"data:{mime};base64," + base64.b64encode(b).decode(), None, (1.0, 1.0)

# ---------------------------------------------------------------- tools
TOOLS = {}
RISKY = set()

def tool(desc, params=None, risky=False):
    def deco(fn):
        TOOLS[fn.__name__] = {"fn": fn, "schema": {"type": "function", "function": {
            "name": fn.__name__, "description": desc,
            "parameters": {"type": "object", "properties": params or {},
                           "required": [k for k, v in (params or {}).items() if not v.pop("optional", False)]}}}}
        if risky: RISKY.add(fn.__name__)
        return fn
    return deco

S = lambda d, **kw: dict({"type": "string", "description": d}, **kw)
N = lambda d, **kw: dict({"type": "number", "description": d}, **kw)

# --- samay / yaad
@tool("Abhi ka date aur time")
def get_time():
    return datetime.datetime.now().strftime("%A, %d %B %Y, %I:%M %p")

@tool("Owner ke baare mein koi baat hamesha ke liye yaad rakho", {"fact": S("yaad rakhne wali baat")})
def remember(fact):
    with _lock:
        if fact not in MEMORY["facts"]: MEMORY["facts"].append(fact)
    save_mem(); return "yaad kar liya"

@tool("Yaad ki hui baat mitao", {"text": S("jo baat hatani hai (uska hissa bhi chalega)")})
def forget(text):
    with _lock:
        before = len(MEMORY["facts"])
        MEMORY["facts"] = [f for f in MEMORY["facts"] if text.lower() not in f.lower()]
    save_mem(); return f"{before - len(MEMORY['facts'])} baat hata di"

@tool("Kuch minute/ghante baad yaad dilao (notification + aawaz)",
      {"minutes": N("kitne minute baad"), "text": S("kya yaad dilana hai")})
def set_reminder(minutes, text):
    due = time.time() + float(minutes) * 60
    with _lock: MEMORY["reminders"].append({"due": due, "text": text})
    save_mem()
    return "reminder laga: " + datetime.datetime.fromtimestamp(due).strftime("%d %b %I:%M %p")

def reminder_loop():
    while True:
        now = time.time(); fire = []
        with _lock:
            keep = []
            for r in MEMORY["reminders"]:
                (fire if r["due"] <= now else keep).append(r)
            if fire: MEMORY["reminders"] = keep
        if fire: save_mem()
        for r in fire:
            notify(APP + " yaad dila raha hai", r["text"]); speak("Yaad dilana tha: " + r["text"])
        time.sleep(20)

# --- internet
def _wiki_search(query, lang="en"):
    try:
        r = json.loads(http(f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=5&srsearch="
                            + urllib.parse.quote(query), timeout=20))
        return "\n".join(f"- {h['title']} (Wikipedia)\n  {strip_html(h.get('snippet',''))}\n  https://{lang}.wikipedia.org/wiki/"
                         + urllib.parse.quote(h['title'].replace(' ', '_')) for h in r.get("query", {}).get("search", []))
    except Exception as e:
        return ""

@tool("Internet par khojo (taaza khabar, jaankari, daam, mausam)", {"query": S("kya khojna hai")})
def web_search(query):
    """Khula internet: DuckDuckGo -> DuckDuckGo lite -> Wikipedia (ek fail ho to doosra)."""
    try:
        page = http("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query), timeout=25)
    except Exception as e:
        page = ""
    if "result__a" not in page:
        try:
            lite = http("https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(query), timeout=25)
            links = re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*class=.result-link.[^>]*>(.*?)</a>', lite, re.S)
            if links: return "\n".join(f"- {strip_html(t)}\n  {u}" for u, t in links[:6])
        except Exception: pass
        w = _wiki_search(query) or _wiki_search(query, "hi")
        return w or "search fail: internet ya search engine se jawab nahi mila"
    out = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', page, re.S):
        url = m.group(1)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("uddg")
        if q: url = q[0]
        out.append(f"- {strip_html(m.group(2))}\n  {strip_html(m.group(3))}\n  {url}")
        if len(out) >= 6: break
    return "\n".join(out) or "kuch nahi mila"

@tool("Kisi web page ka text padho", {"url": S("page ka link")})
def read_webpage(url):
    try: return strip_html(http(url, timeout=30))[:6000]
    except Exception as e: return f"page nahi khula: {e}"

@tool("Phone mein link / website kholo", {"url": S("link")})
def open_url(url):
    if has("termux-open-url"): return sh(["termux-open-url", url])
    return sh(["am", "start", "-a", "android.intent.action.VIEW", "-d", url])

@tool("YouTube par gaana/video chalao ya khojo", {"query": S("kya chalana hai")})
def play_youtube(query):
    return open_url("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query))

@tool("Rasta / jagah Google Maps mein dikhao", {"place": S("jagah ka naam")})
def open_maps(place):
    return open_url("https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(place))

# --- apps
_pkgs = {"whatsapp": "com.whatsapp", "youtube": "com.google.android.youtube", "instagram": "com.instagram.android",
         "chrome": "com.android.chrome", "camera": "android.media.action.STILL_IMAGE_CAMERA", "gmail": "com.google.android.gm",
         "maps": "com.google.android.apps.maps", "settings": "android.settings.SETTINGS", "telegram": "org.telegram.messenger",
         "spotify": "com.spotify.music", "facebook": "com.facebook.katana", "phonepe": "com.phonepe.app",
         "paytm": "net.one97.paytm", "gpay": "com.google.android.apps.nbu.paisa.user", "play store": "com.android.vending",
         "calculator": "com.google.android.calculator", "files": "com.google.android.documentsui", "snapchat": "com.snapchat.android"}

@tool("Phone ka koi bhi app kholo", {"app": S("app ka naam, jaise whatsapp, youtube, camera")})
def open_app(app):
    name = app.lower().strip()
    target = _pkgs.get(name)
    if target and "." in target and target.startswith("android."):
        return sh(["am", "start", "-a", target])
    if not target:
        lst = sh(["pm", "list", "packages"], 20)
        cands = [l.replace("package:", "").strip() for l in lst.splitlines() if name.replace(" ", "") in l.lower()]
        if not cands: return f"'{app}' naam ka app nahi mila"
        target = sorted(cands, key=len)[0]
    if CFG.get("adb_target"):
        return adb("shell", "monkey", "-p", target, "-c", "android.intent.category.LAUNCHER", "1")
    out = sh(["am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", target])
    if "Error" in out or "error" in out:
        out += "\n(Tip: Settings > Apps > Termux > 'Display over other apps' ON karo)"
    return out

@tool("Phone ke installed apps ki list (naam se filter)", {"filter": S("naam ka hissa", optional=True)})
def list_apps(filter=""):
    lst = sh(["pm", "list", "packages"], 20)
    p = [l.replace("package:", "") for l in lst.splitlines() if filter.lower() in l.lower()]
    return "\n".join(p[:80]) or lst

# --- phone (termux-api)
@tool("Battery kitni hai")
def battery(): return sh(["termux-battery-status"])

@tool("Torch / flashlight on ya off", {"on": {"type": "boolean", "description": "true=on"}})
def torch(on): return sh(["termux-torch", "on" if on else "off"])

@tool("Volume set karo", {"stream": S("music, ring, alarm, notification, call"), "level": N("0-15")})
def set_volume(stream, level): return sh(["termux-volume", stream, str(int(level))])

@tool("Screen brightness 0-255 set karo", {"level": N("0-255 ya -1 auto")})
def brightness(level): return sh(["termux-brightness", "auto" if int(level) < 0 else str(int(level))])

@tool("Phone vibrate karo")
def vibrate(): return sh(["termux-vibrate", "-d", "600"])

@tool("Clipboard ka text padho")
def clipboard_get(): return sh(["termux-clipboard-get"])

@tool("Clipboard mein text daalo", {"text": S("text")})
def clipboard_set(text): return sh(["termux-clipboard-set"], inp=text)

@tool("Phone par notification dikhao", {"title": S("heading"), "text": S("sandesh")})
def notify(title, text): return sh(["termux-notification", "--title", title, "--content", text, "--sound"])

@tool("Phone par aayi notifications padho (WhatsApp, SMS waghera)")
def read_notifications():
    out = sh(["termux-notification-list"], 20)
    try:
        items = json.loads(out)
        return "\n".join(f"[{i.get('packageName','')}] {i.get('title','')}: {i.get('content','')}" for i in items[-25:]) or "koi notification nahi"
    except Exception:
        return out

@tool("Abhi ki location (GPS)")
def location(): return sh(["termux-location", "-p", "network", "-r", "once"], 60)

@tool("Wifi / network ki jaankari")
def wifi_info(): return sh(["termux-wifi-connectioninfo"])

@tool("Contact khojo naam se, number lautata hai", {"name": S("naam")})
def find_contact(name):
    out = sh(["termux-contact-list"], 40)
    try:
        cs = json.loads(out)
        hit = [f"{c['name']}: {c['number']}" for c in cs if name.lower() in c.get("name", "").lower()]
        return "\n".join(hit[:15]) or "contact nahi mila"
    except Exception:
        return out

@tool("Haal ke SMS padho", {"count": N("kitne", optional=True)})
def read_sms(count=10): return sh(["termux-sms-list", "-l", str(int(count or 10))], 30)

@tool("SMS bhejo", {"number": S("phone number"), "text": S("sandesh")}, risky=True)
def send_sms(number, text): return sh(["termux-sms-send", "-n", number, text])

@tool("Phone call lagao", {"number": S("phone number")}, risky=True)
def call(number): return sh(["termux-telephony-call", number])

@tool("WhatsApp par sandesh likh kar kholo (number desh code ke saath, jaise 9198xxxxxx)",
      {"number": S("number"), "text": S("sandesh")}, risky=True)
def whatsapp(number, text):
    num = re.sub(r"\D", "", number)
    if len(num) == 10: num = "91" + num
    r = open_url(f"https://wa.me/{num}?text=" + urllib.parse.quote(text))
    if CFG.get("adb_target"):
        time.sleep(4); r += "\n(WhatsApp khul gaya; Send button dabane ke liye look_screen + tap use karo)"
    return r

@tool("Alarm lagao", {"hour": N("0-23"), "minute": N("0-59"), "label": S("naam", optional=True)})
def set_alarm(hour, minute, label=APP):
    return sh(["am", "start", "-a", "android.intent.action.SET_ALARM",
               "--ei", "android.intent.extra.alarm.HOUR", str(int(hour)),
               "--ei", "android.intent.extra.alarm.MINUTES", str(int(minute)),
               "--es", "android.intent.extra.alarm.MESSAGE", label or APP,
               "--ez", "android.intent.extra.alarm.SKIP_UI", "true"])

# --- dekhna (vision)
PENDING_IMAGES = []   # tool ke baad model ko dikhayi jaane wali tasveerein

@tool("Camera se photo lekar dekho (aage=1, peeche=0)", {"camera": N("0 peeche wala, 1 selfie", optional=True)})
def look_camera(camera=0):
    p = os.path.join(SHOTS, f"cam_{int(time.time())}.jpg")
    out = sh(["termux-camera-photo", "-c", str(int(camera or 0)), p], 40)
    if not os.path.exists(p): return "photo nahi bani: " + out
    url, size, _ = image_to_dataurl(p)
    PENDING_IMAGES.append(("camera photo", url)); return f"photo li ({p}). Tasveer aage di gayi hai."

@tool("Phone ki screen dekho (screenshot). Screen chalane se pehle hamesha ye chalao.")
def look_screen():
    data = adb("exec-out", "screencap", "-p", binary=True)
    if isinstance(data, str): return data
    if not data or len(data) < 1000: return "screenshot nahi mila (wireless debugging chalu hai?)"
    p = os.path.join(SHOTS, "screen.png")
    with open(p, "wb") as f: f.write(data)
    url, size, (sx, sy) = image_to_dataurl(p, 720)
    _screen_scale.update(sx=sx, sy=sy)
    PENDING_IMAGES.append(("phone screen", url))
    s = f"{size[0]}x{size[1]}" if size else "asli size"
    return f"screen dekhi. Tasveer {s} hai; tap ke x,y isi tasveer ke hisaab se do."

@tool("Pehle se bani ya mili tasveer dekho (file path)", {"path": S("file ka path")})
def look_file(path):
    p = os.path.expanduser(path)
    if not os.path.exists(p): return "file nahi mili"
    url, _, _ = image_to_dataurl(p); PENDING_IMAGES.append((os.path.basename(p), url)); return "tasveer aage di gayi hai"

# --- screen chalana (ADB)
@tool("Screen par tap karo (look_screen wali tasveer ke x,y)", {"x": N("x"), "y": N("y")})
def tap(x, y):
    return adb("shell", "input", "tap", str(int(x * _screen_scale["sx"])), str(int(y * _screen_scale["sy"])))

@tool("Screen par swipe/scroll karo (tasveer ke x,y)", {"x1": N(""), "y1": N(""), "x2": N(""), "y2": N("")})
def swipe(x1, y1, x2, y2):
    sx, sy = _screen_scale["sx"], _screen_scale["sy"]
    return adb("shell", "input", "swipe", *[str(int(v)) for v in (x1 * sx, y1 * sy, x2 * sx, y2 * sy)], "350")

@tool("Selected box mein text type karo", {"text": S("text")})
def type_text(text):
    safe = text.replace(" ", "%s")
    safe = re.sub(r"([\"'&|;<>()$`\\])", r"\\\1", safe)
    return adb("shell", "input", "text", safe)

@tool("Button dabao: back, home, recent, enter, power, volume_up, volume_down", {"key": S("button")})
def press_key(key):
    codes = {"back": 4, "home": 3, "recent": 187, "enter": 66, "power": 26, "volume_up": 24, "volume_down": 25, "delete": 67}
    return adb("shell", "input", "keyevent", str(codes.get(key.lower(), key)))

@tool("Phone ki screen band (lock) karo. VISUAL chalta rahega aur sunta rahega.")
def screen_off():
    if CFG.get("adb_target"): return adb("shell", "input", "keyevent", "223")
    return "Screen khud band karne ke liye 'visual adb' jodna padega. Abhi power button daba do, main phir bhi sunta rahunga."

@tool("Phone ki screen chalu (jagao) karo")
def screen_on():
    if CFG.get("adb_target"): return adb("shell", "input", "keyevent", "224")
    return "Screen jagane ke liye 'visual adb' jodna padega."

# --- banana (creations)
def _safe(name):
    name = os.path.basename(name.strip()) or "file.txt"
    return os.path.join(CREATIONS, name)

@tool("Khud koi file banao: code, kahani, html page, notes (creations folder mein)",
      {"filename": S("file ka naam, jaise game.html"), "content": S("poora content")})
def create_file(filename, content):
    p = _safe(filename)
    with open(p, "w", encoding="utf-8") as f: f.write(content)
    port = CFG["web_port"]
    return f"ban gayi: {p}\nDekhne ka link: http://127.0.0.1:{port}/creations/{os.path.basename(p)}"

@tool("Banayi hui file padho", {"filename": S("naam")})
def read_creation(filename):
    p = _safe(filename)
    if not os.path.exists(p): return "file nahi mili. Bani files: " + ", ".join(os.listdir(CREATIONS))
    with open(p, encoding="utf-8", errors="replace") as f: return f.read()[:8000]

@tool("Banayi hui cheezon ki list")
def list_creations(): return "\n".join(sorted(os.listdir(CREATIONS))) or "abhi kuch nahi bana"

@tool("Banayi file/page ko phone ke browser mein kholo", {"filename": S("naam")})
def open_creation(filename):
    return open_url(f"http://127.0.0.1:{CFG['web_port']}/creations/{os.path.basename(filename)}")

@tool("Python code chala kar nateeja lo (hisaab, code test, data). creations folder mein chalta hai.", {"code": S("python code")})
def run_python(code):
    p = os.path.join(CREATIONS, "_run.py")
    with open(p, "w", encoding="utf-8") as f: f.write(code)
    try:
        r = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=60, cwd=CREATIONS)
        out = (r.stdout or "") + (("\nERROR:\n" + r.stderr) if r.stderr.strip() else "")
        return (out.strip() or "ok (koi output nahi)")[:6000]
    except subprocess.TimeoutExpired:
        return "ERROR: 60 second se zyada chala, roka gaya."

@tool("Termux shell command chalao", {"command": S("command")}, risky=True)
def run_shell(command): return sh(command, 90)[:6000]

# ---------------------------------------------------------------- BUILDER AGENT (asli projects)
PROJECTS = os.path.expanduser(CFG.get("projects_dir") or "~/visual-projects")
SECRETS = os.path.join(HOME, "secrets.json")
os.makedirs(PROJECTS, exist_ok=True)
DANGER = re.compile(r"(rm\s+-rf\s+(/|~|\$HOME)(\s|$)|\bsudo\b|mkfs|dd\s+if=|>\s*/dev/|:\(\)\s*\{|chmod\s+-R\s+777\s+/|git\s+push\s+.*--force|gh\s+repo\s+delete)", re.I)

def _slug(name):
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip()).strip("-").lower()
    return s or "project"

def _proj(name):
    p = os.path.join(PROJECTS, _slug(name))
    if not os.path.isdir(p): raise ValueError(f"project '{name}' nahi mila. Pehle project_create chalao. Projects: {', '.join(os.listdir(PROJECTS)) or 'koi nahi'}")
    return p

def _inside(root, rel):
    p = os.path.realpath(os.path.join(root, rel))
    if not (p == root or p.startswith(os.path.realpath(root) + os.sep)): raise ValueError("project folder ke bahar file nahi")
    return p

def _env():
    env = dict(os.environ)
    try: env.update({k: str(v) for k, v in load_json(SECRETS, {}).items()})
    except Exception: pass
    return env

def _run(cmd, cwd, timeout=300):
    if DANGER.search(cmd): return "ROKA: ye command khatarnak hai (system mita sakta hai). Iske bina karo ya owner se poochho."
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=_env())
        out = (r.stdout or "")[-4000:] + (("\nSTDERR:\n" + r.stderr[-3000:]) if r.stderr.strip() else "")
        return f"[exit {r.returncode}]\n" + (out.strip() or "(koi output nahi)")
    except subprocess.TimeoutExpired:
        return f"ERROR: {timeout}s se zyada chala, roka gaya."

@tool("Naya project (app/game/website/tool/system) shuru karo: alag folder + git. Har bade kaam ke liye pehle ye.",
      {"name": S("chhota naam, jaise doctor-app"), "about": S("project kya karega, 1-2 line")})
def project_create(name, about):
    p = os.path.join(PROJECTS, _slug(name))
    os.makedirs(p, exist_ok=True)
    if not os.path.exists(os.path.join(p, ".gitignore")):
        with open(os.path.join(p, ".gitignore"), "w") as f:
            f.write(".env\n*.key\nsecrets*\nnode_modules/\n__pycache__/\n*.pyc\n.venv/\n")
    if not os.path.exists(os.path.join(p, "README.md")):
        with open(os.path.join(p, "README.md"), "w", encoding="utf-8") as f: f.write(f"# {name}\n\n{about}\n")
    if not os.path.isdir(os.path.join(p, ".git")): sh(["git", "init", "-q", "-b", "main", p], 20)
    return f"project taiyaar: {p}\nPreview link (html ho to): http://127.0.0.1:{CFG['web_port']}/p/{_slug(name)}/"

@tool("Project mein file likho/badlo (poora content). Folder apne aap banta hai.",
      {"project": S("project naam"), "path": S("file path, jaise src/app.py ya index.html"), "content": S("poora content")})
def project_write(project, path, content):
    root = _proj(project); f = _inside(root, path)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fh: fh.write(content)
    return f"likha: {path} ({len(content)} chars)"

@tool("Project ki file padho", {"project": S("project"), "path": S("file path")})
def project_read(project, path):
    f = _inside(_proj(project), path)
    with open(f, encoding="utf-8", errors="replace") as fh: return fh.read()[:12000]

@tool("Project ki saari files ki list", {"project": S("project")})
def project_files(project):
    root = _proj(project); out = []
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in (".git", "node_modules", "__pycache__", ".venv")]
        for x in fs: out.append(os.path.relpath(os.path.join(d, x), root))
    return "\n".join(sorted(out)[:300]) or "khaali"

@tool("Project folder mein command chalao (test, build, python app.py, npm test, git...). Bina pooche chalta hai; khatarnak command apne aap rukte hain.",
      {"project": S("project"), "command": S("shell command"), "timeout": N("second, default 300", optional=True)})
def project_run(project, command, timeout=300):
    return _run(command, _proj(project), int(timeout or 300))

@tool("Zaroori package install karo. manager: pip (python library), pkg (Termux tool jaise nodejs, ffmpeg, git), npm (project ke andar JS library).",
      {"manager": S("pip | pkg | npm"), "packages": S("naam, space se alag"), "project": S("npm ke liye project naam", optional=True)})
def install_packages(manager, packages, project=""):
    pk = " ".join(re.findall(r"[A-Za-z0-9@._/=<>~+-]+", packages))
    if not pk: return "koi package naam nahi"
    m = manager.lower().strip()
    if m == "pip": return _run(f"{sys.executable} -m pip install {pk}", HOME, 900)
    if m == "pkg": return _run(f"pkg install -y {pk}" if has("pkg") else f"echo 'pkg sirf Termux mein'; false", HOME, 900)
    if m == "npm": return _run(f"npm install {pk}", _proj(project) if project else HOME, 900)
    return "manager pip, pkg ya npm hona chahiye"

@tool("Internet se file (free music, sound, image, font, data) project mein download karo. Licence free/CC0 ho, aur README mein credit likho.",
      {"project": S("project"), "url": S("seedha file ka link"), "path": S("kahan rakhna hai, jaise assets/bg.mp3")})
def download_file(project, url, path):
    f = _inside(_proj(project), path); os.makedirs(os.path.dirname(f), exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 VISUAL"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read(60_000_000); ctype = r.headers.get("Content-Type", "")
        if "text/html" in ctype and not path.endswith((".html", ".htm")):
            return f"ye seedha file nahi, web page hai ({ctype}). Asli file ka link dhoondho."
        with open(f, "wb") as fh: fh.write(data)
        return f"download hua: {path} ({len(data)//1024} KB, {ctype})"
    except Exception as e:
        return f"download fail: {e}"

@tool("API key / password jaisi secret cheez save karo (project ke commands mein env variable bankar milti hai, GitHub par kabhi nahi jaati). Sirf owner ki di hui value.",
      {"name": S("jaise OPENWEATHER_API_KEY"), "value": S("value")})
def save_secret(name, value):
    d = load_json(SECRETS, {}); d[re.sub(r"[^A-Z0-9_]", "_", name.upper())] = value
    save_json(SECRETS, d); os.chmod(SECRETS, 0o600)
    return f"{name} save ho gaya (sirf is phone par)."

@tool("Kaunse secrets/keys save hain (sirf naam)")
def list_secrets(): return ", ".join(load_json(SECRETS, {}).keys()) or "koi nahi"

@tool("Project ko owner ke GitHub par ALAG repo banakar daalo (ya pehle se bana ho to update push). Link lautata hai.",
      {"project": S("project"), "repo": S("GitHub repo naam (khaali = project naam)", optional=True),
       "private": {"type": "boolean", "description": "true = private (default)", "optional": True}, "message": S("commit message", optional=True)})
def github_publish(project, repo="", private=True, message="VISUAL update"):
    root = _proj(project); repo = _slug(repo or project)
    if not has("gh"): return "gh nahi hai. Termux mein: pkg install gh && gh auth login"
    st = _run("gh auth status", root, 30)
    if "Logged in" not in st and "logged in" not in st: return "GitHub login nahi hai. Termux mein chalao: gh auth login\n" + st
    # commit se PEHLE har file jaancho: key mili to kuch commit/push nahi
    pat = re.compile(r"(AIza[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|gsk_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")
    hits = []
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in (".git", "node_modules", ".venv", "__pycache__")]
        for x in fs:
            fp = os.path.join(d, x)
            try:
                if os.path.getsize(fp) > 2_000_000: continue
                with open(fp, encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if pat.search(line): hits.append(f"{os.path.relpath(fp, root)}:{i}")
            except Exception: pass
    if hits: return "ROKA: in jagah secret key likhi hai, GitHub par kuch nahi bheja: " + ", ".join(hits[:10]) + ". Key hata kar env variable (save_secret) use karo."
    out = [_run('git add -A && git -c user.name="VISUAL" -c user.email="visual@users.noreply.github.com" commit -qm "%s" || true' % message.replace('"', "'"), root, 60)]
    has_remote = "origin" in _run("git remote", root, 20)
    if not has_remote:
        out.append(_run(f"gh repo create {repo} {'--private' if private is not False else '--public'} --source . --remote origin --push", root, 180))
    else:
        out.append(_run("git push -u origin HEAD", root, 180))
    user = _run("gh api user --jq .login", root, 30).splitlines()[-1].strip()
    return "\n".join(out)[-2500:] + f"\nRepo link: https://github.com/{user}/{repo}"

@tool("Project ka html/web page phone ke browser mein kholo (preview)", {"project": S("project"), "path": S("jaise index.html", optional=True)})
def project_preview(project, path="index.html"):
    _proj(project)
    return open_url(f"http://127.0.0.1:{CFG['web_port']}/p/{_slug(project)}/{path or 'index.html'}")

@tool("Saare projects ki list")
def list_projects(): return "\n".join(sorted(os.listdir(PROJECTS))) or "abhi koi project nahi"

@tool("Gehri research: kai khoj + top pages padh kar saar nikaalo (sources ke saath). Mushkil/naye sawaal, tulna, taaza jaankari ke liye.",
      {"question": S("kya pata karna hai"), "queries": S("2-4 alag khoj, | se alag (khaali = question hi)", optional=True)})
def deep_research(question, queries=""):
    qs = [q.strip() for q in (queries or question).split("|") if q.strip()][:4]
    seen, notes = set(), []
    for q in qs:
        res = web_search(q)
        urls = re.findall(r"\n  (https?://\S+)", "\n" + res)
        notes.append(f"## Khoj: {q}\n{res[:1500]}")
        for u in urls[:2]:
            dom = urllib.parse.urlparse(u).netloc
            if u in seen or len(seen) >= 6: continue
            seen.add(u)
            txt = read_webpage(u)
            notes.append(f"## Page: {dom}\n{u}\n{txt[:2200]}")
    notes.append("Niyam: jawab sirf in sources par tikao, site ka naam batao; sources mein takraav ho to batao.")
    return "\n\n".join(notes)[:14000]

@tool("Web project (HTML/JS) ko internet par LIVE karo (GitHub Pages). Repo PUBLIC hona zaroori hai (free plan). Live link deta hai.",
      {"project": S("project"), "confirm_public": {"type": "boolean", "description": "owner ne public karne ki haan kahi"}})
def deploy_web(project, confirm_public=False):
    root = _proj(project)
    if not confirm_public: return "Pehle owner se poochho: GitHub Pages ke liye repo PUBLIC karna padega (code sab dekh sakenge). Haan ho to confirm_public=true."
    pub = github_publish(project, private=False)
    if pub.startswith("ROKA") or "login nahi" in pub: return pub
    repo = _slug(project)
    user = _run("gh api user --jq .login", root, 30).splitlines()[-1].strip()
    _run(f"gh repo edit {user}/{repo} --visibility public --accept-visibility-change-consequences", root, 60)
    r = _run(f"gh api -X POST repos/{user}/{repo}/pages -f 'source[branch]=main' -f 'source[path]=/'", root, 60)
    if "already" in r.lower() or "409" in r: r = "(Pages pehle se chalu)"
    return f"{r[-500:]}\nLive link (1-2 minute mein khulega): https://{user}.github.io/{repo}/"

# ---------------------------------------------------------------- SACH ENGINE (jhooth pakadna, sach nikaalna)
def llm_one(provider, prompt, system="Tum ek sachche expert ho. Pakka na pata ho to 'PAKKA NAHI' likho. Kuch gadho mat.", timeout=60):
    """Ek hi provider se seedha jawab (tools ke bina). (text, error)"""
    info = PROVIDERS[provider]; model = CFG.get("models", {}).get(provider) or info["model"]
    body = {"model": model, "temperature": 0.2, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    try:
        r = json.loads(http(info["base"].rstrip("/") + "/chat/completions", body, {"Authorization": "Bearer " + CFG["keys"][provider]}, timeout=timeout))
        return (r["choices"][0]["message"].get("content") or "").strip(), ""
    except urllib.error.HTTPError as e:
        return "", f"{e.code} {e.read().decode()[:150]}"
    except Exception as e:
        return "", str(e)[:150]

def _parallel(fns, timeout=90):
    out = [None] * len(fns); ths = []
    for i, f in enumerate(fns):
        t = threading.Thread(target=lambda i=i, f=f: out.__setitem__(i, f()), daemon=True); t.start(); ths.append(t)
    for t in ths: t.join(timeout)
    return out

@tool("SACH ENGINE: ek sawaal ko kai alag AI models se alag-alag poochho + internet ke saboot se milao, jhooth/galti pakdo, aur sabse sachcha jawab bharose ke level ke saath do. "
      "Zaroori tathya, number, code/library/API ki jaankari, ya jab model par shak ho tab use karo.",
      {"question": S("kya pakka karna hai"), "web": {"type": "boolean", "description": "internet saboot bhi lo (default haan)", "optional": True}})
def cross_check(question, web=True):
    provs = providers_available()[:4]
    if not provs: return "koi AI key nahi"
    jobs = [lambda p=p: (p, *llm_one(p, question)) for p in provs]
    if web is not False: jobs.append(lambda: ("WEB", deep_research(question), ""))
    res = _parallel(jobs)
    answers = [(p, a, e) for (p, a, e) in [r for r in res if r] if p != "WEB"]
    evidence = next((a for (p, a, e) in [r for r in res if r] if p == "WEB"), "")
    good = [(p, a) for p, a, e in answers if a]
    if not good: return "Kisi model se jawab nahi mila: " + "; ".join(f"{p}: {e}" for p, a, e in answers)
    blocks = "\n\n".join(f"### Model {i+1} ({p})\n{a[:3000]}" for i, (p, a) in enumerate(good))
    judge = (f"SAWAAL: {question}\n\nAlag-alag AI models ke jawab (inme jhooth ya galti ho sakti hai):\n{blocks}\n\n"
             f"INTERNET SABOOT:\n{evidence[:7000] or '(nahi liya)'}\n\n"
             "Tum ek sakht jaanchne wale ho. Har mukhya baat ko saboot aur doosre jawabon se milao. Jahan models aapas mein ya saboot se mel nahi khaate, "
             "wahi jhooth/galti hai. Jo saboot mein na ho use pakka mat bolo. Output bilkul is format mein:\n"
             "SACH: <sabse sahi jawab, chhota>\nBHAROSA: <ucch|madhyam|kam> (kyun)\nGALAT/SHAK: <kis model ki kaunsi baat galat ya bina saboot>\nSOURCES: <saboot ke links>")
    verdict, err = llm_one(provs[0], judge, system="Tum sach jaanchne wale nyaayadhish ho. Sirf saboot par chalo.", timeout=90)
    agree = f"{len(good)} model ne jawab diya" + (f", {len(answers)-len(good)} fail" if len(answers) > len(good) else "")
    return (verdict or ("Nyaayadhish fail: " + err + "\n\n" + blocks[:3000])) + f"\n\n({agree}; web saboot: {'haan' if evidence else 'nahi'})"

STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}

@tool("Jhoothi/bani hui library pakdo: package sach mein PyPI (pip) ya npm par hai ya nahi, aur kab update hua. Code mein naya package daalne/install karne se PEHLE.",
      {"manager": S("pip ya npm"), "packages": S("naam, space/comma se alag")})
def check_packages(manager, packages):
    out = []
    for name in [x for x in re.split(r"[\s,]+", packages) if x][:15]:
        base = re.split(r"[<>=!~\[]", name)[0]
        try:
            if manager.lower().startswith("p"):
                if base in STDLIB: out.append(f"✅ {base}: Python ki apni (stdlib), install nahi chahiye"); continue
                d = json.loads(http(f"https://pypi.org/pypi/{urllib.parse.quote(base)}/json", timeout=20))
                rel = d.get("releases", {}).get(d["info"]["version"], [{}]); up = (rel[-1] if rel else {}).get("upload_time", "?")[:10]
                out.append(f"✅ {base}: asli hai (PyPI v{d['info']['version']}, {up}) - {(d['info'].get('summary') or '')[:80]}")
            else:
                d = json.loads(http(f"https://registry.npmjs.org/{urllib.parse.quote(base, safe='@/')}", timeout=20))
                v = d.get("dist-tags", {}).get("latest", "?"); up = d.get("time", {}).get(v, "?")[:10]
                out.append(f"✅ {base}: asli hai (npm v{v}, {up}) - {(d.get('description') or '')[:80]}")
        except urllib.error.HTTPError as e:
            out.append(f"❌ {base}: NAHI MILA ({e.code}) - ye bani hui/jhoothi library ho sakti hai, ISTEMAAL MAT KARO")
        except Exception as e:
            out.append(f"⚠️ {base}: jaanch nahi ho payi ({str(e)[:60]})")
    return "\n".join(out)

@tool("API/website link zinda hai ya nahi (status code, type). Code mein koi API URL daalne se pehle.", {"url": S("link")})
def check_url(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 VISUAL"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(400).decode("utf-8", "replace")
            return f"✅ zinda: HTTP {r.status}, {r.headers.get('Content-Type','')}\nshuruaat: {strip_html(body)[:200]}"
    except urllib.error.HTTPError as e:
        return f"⚠️ HTTP {e.code} (server hai, par ye link/key/method galat ho sakta hai): {e.read(200).decode('utf-8','replace')[:150]}"
    except Exception as e:
        return f"❌ nahi khula: {str(e)[:120]} (ye API shayad maujood hi nahi)"

@tool("Project ka code SACH mein sahi hai ya nahi jaancho: syntax/compile, imports ki libraries asli hain ya nahi, aur tests chalao. 'Ho gaya' bolne se pehle hamesha.",
      {"project": S("project naam")})
def verify_code(project):
    root = _proj(project); rep = []; imports = set(); npm = set()
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in (".git", "node_modules", ".venv", "__pycache__")]
        for f in fs:
            fp = os.path.join(d, f); rel = os.path.relpath(fp, root)
            if f.endswith(".py"):
                r = _run(f'{sys.executable} -m py_compile "{fp}"', root, 60)
                rep.append(("✅ " if "[exit 0]" in r else "❌ ") + rel + ("" if "[exit 0]" in r else ": " + r[-300:]))
                src = open(fp, encoding="utf-8", errors="ignore").read()
                for m in re.finditer(r"^\s*(?:from\s+([A-Za-z_][\w]*)|import\s+([A-Za-z_][\w]*))", src, re.M):
                    mod = m.group(1) or m.group(2)
                    if mod not in STDLIB and not os.path.exists(os.path.join(root, mod + ".py")) and not os.path.isdir(os.path.join(root, mod)):
                        imports.add(mod)
            elif f.endswith((".js", ".mjs")) and has("node"):
                r = _run(f'node --check "{fp}"', root, 60)
                rep.append(("✅ " if "[exit 0]" in r else "❌ ") + rel + ("" if "[exit 0]" in r else ": " + r[-300:]))
            elif f == "package.json":
                try: npm |= set(json.load(open(fp)).get("dependencies", {}).keys())
                except Exception as e: rep.append(f"❌ package.json kharab: {e}")
            elif f.endswith((".html", ".htm")):
                h = open(fp, encoding="utf-8", errors="ignore").read()
                for src_ in re.findall(r'<script[^>]+src="([^"]+)"', h):
                    if not src_.startswith("http") and not os.path.exists(os.path.join(os.path.dirname(fp), src_)):
                        rep.append(f"❌ {rel}: script '{src_}' file maujood nahi")
    PIPNAME = {"cv2": "opencv-python", "PIL": "pillow", "sklearn": "scikit-learn", "yaml": "pyyaml", "bs4": "beautifulsoup4", "dotenv": "python-dotenv"}
    if imports: rep.append("Python libraries:\n" + check_packages("pip", " ".join(PIPNAME.get(m, m) for m in sorted(imports))))
    if npm: rep.append("npm libraries:\n" + check_packages("npm", " ".join(sorted(npm))))
    tests = [f for f in os.listdir(root) if re.match(r"test.*\.py$", f)]
    if tests: rep.append("Tests:\n" + _run(f"{sys.executable} -m unittest discover -p 'test*.py' 2>&1 || {sys.executable} {tests[0]}", root, 180)[-1200:])
    bad = sum(1 for r in rep if "❌" in r)
    return ("NATEEJA: " + ("SAB SAHI ✅" if not bad else f"{bad} GALTI ❌, pehle theek karo") + "\n" + "\n".join(rep))[:7000]

# ---------------------------------------------------------------- KHUD KO UPGRADE (self-improvement)
PLUGINS = os.path.join(HERE, "plugins")
BACKUPS = os.path.join(HOME, "backups")
os.makedirs(PLUGINS, exist_ok=True); os.makedirs(BACKUPS, exist_ok=True)
# ye cheezein kisi upgrade mein hatni nahi chahiye (suraksha)
PROTECTED = ["DANGER = re.compile", "RISKY.add", "CRISIS = re.compile", "14416", "ROKA: in jagah secret",
             "def _inside(", "confirm_risky", "def _ok_pin("]
PLUGIN_ERRORS = {}
RESTART_PENDING = {"v": False}

def _self_path(path):
    p = os.path.realpath(os.path.join(HERE, path))
    if not (p == HERE or p.startswith(os.path.realpath(HERE) + os.sep)) or "/.git" in p:
        raise ValueError("sirf VISUAL ke apne folder ki files")
    return p

def load_plugins():
    """plugins/*.py ko VISUAL ke andar load karo; har plugin @tool se naye kaam jod sakta hai."""
    PLUGIN_ERRORS.clear(); loaded = []
    for fn in sorted(os.listdir(PLUGINS)):
        if fn.startswith(("_", ".")): continue
        path = os.path.join(PLUGINS, fn)
        if os.path.isdir(path):                      # bada plugin: plugins/<naam>/plugin.py + apne modules
            entry = os.path.join(path, "plugin.py")
            if not os.path.exists(entry): continue
            if path not in sys.path: sys.path.insert(0, path)
        elif fn.endswith(".py"): entry = path
        else: continue
        try:
            with open(entry, encoding="utf-8") as f: code = f.read()
            g = globals(); g["PLUGIN_DIR"] = os.path.dirname(entry)
            exec(compile(code, entry, "exec"), g)
            loaded.append(fn)
        except Exception as e:
            import traceback
            PLUGIN_ERRORS[fn] = f"{type(e).__name__}: {e} | {traceback.format_exc()[-400:]}"
    return loaded

def _backup(label):
    d = os.path.join(BACKUPS, time.strftime("%Y%m%d-%H%M%S") + f"{int(time.time()*1000)%1000:03d}-" + _slug(label)[:30])
    shutil.copytree(HERE, d, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    olds = sorted(os.listdir(BACKUPS))
    for o in olds[:-15]: shutil.rmtree(os.path.join(BACKUPS, o), ignore_errors=True)
    return d

def _self_check():
    """Naya code chal sakta hai ya nahi: compile + alag process mein import + tools ginti + suraksha."""
    with open(os.path.join(HERE, "visual.py"), encoding="utf-8") as f: core = f.read()
    core_wo = re.sub(r"PROTECTED = \[.*?\]\n", "", core, count=1, flags=re.S)   # list khud gin-ti mein nahi
    missing = [x for x in PROTECTED if x not in core_wo]
    if missing: return False, "Suraksha ke hisse hat gaye: " + ", ".join(missing)
    test = ("import sys,os;sys.argv=['x'];sys.path.insert(0,%r);import visual as v;"
            "print('TOOLS',len(v.TOOLS));print('PLUGIN_ERRORS',v.PLUGIN_ERRORS);"
            "import json;json.dumps(v.live_tools());v.system_prompt()") % HERE
    env = dict(os.environ); env["VISUAL_SELFTEST"] = "1"
    r = subprocess.run([sys.executable, "-c", test], capture_output=True, text=True, timeout=90, cwd=HERE, env=env)
    out = (r.stdout + r.stderr)[-2500:]
    if r.returncode != 0 or "PLUGIN_ERRORS {}" not in r.stdout: return False, out
    return True, out

@tool("Apna (VISUAL ka) code padho, taaki khud ko samajh kar upgrade kar sako. path: visual.py, web/index.html, web/live.js, plugins/<naam>.py. "
      "Badi file ho to 'find' se khoj ke hisse padho.",
      {"path": S("file"), "find": S("ye shabd jahan ho uske aas-paas ka hissa (optional)", optional=True)})
def self_read(path, find=""):
    p = _self_path(path)
    if not os.path.exists(p): return "file nahi hai. Files: " + ", ".join(sorted(os.listdir(HERE))) + " | plugins: " + ", ".join(os.listdir(PLUGINS))
    with open(p, encoding="utf-8", errors="replace") as f: text = f.read()
    if find:
        out = []; lines = text.splitlines()
        for i, l in enumerate(lines):
            if find.lower() in l.lower(): out.append("\n".join(f"{j+1}: {lines[j]}" for j in range(max(0, i-8), min(len(lines), i+25))))
            if len(out) >= 4: break
        return ("\n...\n".join(out) or "nahi mila")[:12000]
    return text[:12000] + (f"\n... (kul {len(text)} akshar; 'find' se aage ke hisse padho)" if len(text) > 12000 else "")

@tool("KHUD KO UPGRADE: naya plugin banao/badlo (plugins/<naam>.py). Naye kaam/integration ke liye SABSE ACHHA rasta. "
      "Plugin mein seedha @tool(...) decorator se function likho; VISUAL ke helpers (sh, http, S, N, CFG, MEMORY, run_tool, web_search, _run) mil jaate hain. "
      "Save ke baad apne aap test hota hai; fail ho to purana wapas.",
      {"name": S("plugin naam, jaise weather"), "code": S("poora python code")})
def self_plugin(name, code):
    fn = _slug(name).replace("-", "_") + ".py"; p = os.path.join(PLUGINS, fn)
    bk = _backup("plugin-" + name)
    with open(p, "w", encoding="utf-8") as f: f.write(code)
    ok, out = _self_check()
    if not ok:
        shutil.copy2(os.path.join(bk, "plugins", fn), p) if os.path.exists(os.path.join(bk, "plugins", fn)) else os.remove(p)
        return "FAIL, purana wapas laga diya. Galti theek karke dobara try karo:\n" + out
    return f"plugin '{fn}' save aur test pass. Ab self_restart chalao taaki naye kaam chalu ho jaayen.\n{out[-300:]}"

@tool("KHUD KO UPGRADE: apne main code (visual.py / web/index.html / web/live.js) mein ek hissa badlo. 'old' bilkul waisa hi ho jaisa file mein hai (self_read se dekho). "
      "Pehle backup, phir test; fail ho to apne aap purana wapas. Suraksha wale hisse nahi hat sakte.",
      {"path": S("file"), "old": S("purana text (bilkul exact, file mein ek hi baar)"), "new": S("naya text")})
def self_edit(path, old, new):
    p = _self_path(path)
    if not os.path.isfile(p):
        return f"'{path}' file nahi hai. VISUAL ki files: visual.py, web/index.html, web/live.js, plugins/... (self_read se dekho)"
    with open(p, encoding="utf-8") as f: text = f.read()
    n = text.count(old)
    if n != 1: return f"'old' text file mein {n} baar mila (1 baar hona chahiye). self_read(find=...) se exact text dekho."
    bk = _backup("edit-" + os.path.basename(path))
    with open(p, "w", encoding="utf-8") as f: f.write(text.replace(old, new, 1))
    ok, out = _self_check()
    if not ok:
        shutil.copy2(os.path.join(bk, os.path.relpath(p, HERE)), p)
        return "FAIL, badlav wapas le liya (koi nuksaan nahi). Galti:\n" + out
    return f"badlav save + test pass. Ab self_restart chalao.\n{out[-300:]}"

@tool("Upgrade ke baad VISUAL ko restart karo taaki naya code chalu ho (GitHub par bhi bhejta hai). Owner ko bata do ki 5 second mein wapas aaunga.",
      {"note": S("kya upgrade hua (commit message)", optional=True)})
def self_restart(note="self upgrade"):
    ok, out = _self_check()
    if not ok: return "Restart nahi kiya: naya code test mein fail hai.\n" + out
    if os.path.isdir(os.path.join(HERE, ".git")):
        _run('git add -A && git -c user.name="VISUAL" -c user.email="visual@users.noreply.github.com" commit -qm "%s" && git push -q || true' % note.replace('"', "'")[:100], HERE, 90)
    RESTART_PENDING["v"] = True
    def _go():
        time.sleep(2.5)
        os.execv(sys.executable, [sys.executable, os.path.join(HERE, "visual.py")] + [a for a in sys.argv[1:]] + (["--no-open"] if "--no-open" not in sys.argv else []))
    threading.Thread(target=_go, daemon=True).start()
    return "restart ho raha hai (3-5 second). Naye kaam uske baad chalu."

@tool("Pichhla upgrade galat laga to purana version wapas lao (backup se). Phir self_restart.",
      {"which": S("kaunsa backup (khaali = sabse naya)", optional=True)})
def self_rollback(which=""):
    bks = sorted(os.listdir(BACKUPS), key=lambda x: os.path.getmtime(os.path.join(BACKUPS, x)))
    if not bks: return "koi backup nahi"
    b = next((x for x in reversed(bks) if which and which in x), bks[-1]); src = os.path.join(BACKUPS, b)
    for rel in ["visual.py", "web", "plugins"]:
        s_, d_ = os.path.join(src, rel), os.path.join(HERE, rel)
        if os.path.isdir(s_): shutil.rmtree(d_, ignore_errors=True); shutil.copytree(s_, d_)
        elif os.path.exists(s_): shutil.copy2(s_, d_)
    return f"backup '{b}' wapas laga diya. Ab self_restart chalao."

@tool("VISUAL ki apni jaankari: version, kitne tools, plugins, plugin errors, backups")
def self_info():
    return json.dumps({"version": VERSION, "tools": len(TOOLS), "plugins": os.listdir(PLUGINS), "plugin_errors": PLUGIN_ERRORS,
                       "backups": sorted(os.listdir(BACKUPS))[-5:]}, ensure_ascii=False)

# ---------------------------------------------------------------- ADVANCED UPGRADE PIPELINE (research -> spec -> build -> test -> critic)
_CTX = threading.local()          # kis Engineer task ke andar hain

def _pdir(name):
    d = os.path.join(PLUGINS, _slug(name).replace("-", "_"))
    os.makedirs(d, exist_ok=True); return d

@tool("UPGRADE kadam 1-2: bade upgrade ka SPEC likho (plugins/<naam>/SPEC.md): lakshya, research se mili best tareeke/libraries (asli, check_packages se jaanchi), "
      "saare features (world-class version mein kya hota), architecture (kaun si files), galti sambhalna, config/keys, aur PAKKE TEST (acceptance criteria).",
      {"name": S("upgrade/plugin naam"), "spec": S("poora spec markdown")})
def upgrade_spec(name, spec):
    d = _pdir(name)
    with open(os.path.join(d, "SPEC.md"), "w", encoding="utf-8") as f: f.write(spec)
    t = getattr(_CTX, "task", None)
    if t: t["spec"] = True
    return f"SPEC save: {os.path.relpath(d, HERE)}/SPEC.md ({len(spec)} akshar). Ab plugin_file se files banao (entry: plugin.py, test_*.py zaroor)."

@tool("UPGRADE kadam 3: bade plugin ki koi bhi file likho (plugins/<naam>/<path>). Entry file 'plugin.py' (isme @tool functions), baaki modules alag files mein, "
      "aur 'test_*.py' mein unittest wale asli test. Sirf file likhta hai; jaanch plugin_test se.",
      {"name": S("plugin naam"), "path": S("jaise plugin.py, engine.py, test_engine.py"), "content": S("poora content")})
def plugin_file(name, path, content):
    d = _pdir(name); f = _inside(d, path)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    if not os.path.exists(os.path.join(BACKUPS, "_last_" + _slug(name))): _backup("plugin-" + name)
    with open(f, "w", encoding="utf-8") as fh: fh.write(content)
    return f"likha: plugins/{os.path.basename(d)}/{path} ({len(content)} akshar)"

@tool("UPGRADE kadam 4: plugin ki poori jaanch: compile, VISUAL ke saath load (tools judte hain ya nahi), aur test_*.py chalana. Nateeja + galti trace.",
      {"name": S("plugin naam")})
def plugin_test(name):
    d = _pdir(name); rep = []
    if not os.path.exists(os.path.join(d, "plugin.py")): return "❌ plugin.py nahi hai (entry file zaroori)"
    for f in os.listdir(d):
        if f.endswith(".py"):
            r = _run(f'{sys.executable} -m py_compile "{os.path.join(d, f)}"', d, 60)
            if "exit 0" not in r.splitlines()[0]: rep.append(f"❌ compile {f}: {r[-400:]}")
    ok, out = _self_check(); rep.append(("✅" if ok else "❌") + " VISUAL ke saath load: " + out[-500:])
    tests = [f for f in os.listdir(d) if f.startswith("test") and f.endswith(".py")]
    if not tests: rep.append("❌ koi test_*.py nahi: asli test likho")
    else:
        env_cmd = f'cd "{d}" && PYTHONPATH="{d}:{HERE}" VISUAL_SELFTEST=1 {sys.executable} -m unittest discover -p "test*.py" -v 2>&1'
        r = _run(env_cmd, d, 300); passed = re.search(r"\nOK", r) is not None
        n = re.search(r"Ran (\d+) test", r); n = int(n.group(1)) if n else 0
        rep.append(("✅" if passed and n > 0 else "❌") + f" tests: {n} chale\n" + r[-1800:])
    good = not any(x.startswith("❌") for x in rep)
    t = getattr(_CTX, "task", None)
    if t: t["tests_ok"] = good
    return ("NATEEJA: SAB PASS ✅" if good else "NATEEJA: FAIL ❌ (galti theek karo)") + "\n" + "\n".join(rep)[:6000]

CRITIC_SYS = ("Tum ek bahut sakht senior engineer CRITIC ho (duniya ke best product jaise standard). Tumhara kaam kamiyan pakadna hai, tareef nahi. "
              "SPEC aur code padh kar dekho: kya sab features asli mein bane hain ya sirf naam ke; galti sambhalna; edge cases; suraksha; "
              "test asli hain ya dikhawe ke; kya ye 'minimum' hai ya sach mein advanced; nakli library/API. Jawab bilkul is format mein:\n"
              "SCORE: <0-10>\nKAMIYAN:\n- ...\nSUDHAAR (theek kya karna hai, saaf):\n- ...")

@tool("UPGRADE kadam 5: sakht CRITIC (alag nazar) se plugin ki review: SCORE 0-10 + kamiyan + sudhaar. Score 8 se kam ho to sudhaar karke dobara test + critic.",
      {"name": S("plugin naam")})
def critic_review(name):
    d = _pdir(name); parts = []
    for f in sorted(os.listdir(d)):
        fp = os.path.join(d, f)
        if os.path.isfile(fp) and f.endswith((".py", ".md", ".json", ".txt")):
            parts.append(f"===== {f} =====\n" + open(fp, encoding="utf-8", errors="ignore").read()[:9000])
    bundle = "\n\n".join(parts)[:60000]
    provs = providers_available()
    if not provs: return "koi AI key nahi"
    # critic doosre provider se ho to aur behtar (alag nazar); warna smart model
    critic_p = next((p for p in provs[1:] if p in ("openrouter", "mistral", "groq", "cerebras")), provs[0])
    if critic_p == "gemini":
        sm, _ = best_models(); old = CFG.setdefault("models", {}).get("gemini")
        if sm: CFG["models"]["gemini"] = sm
        txt, err = llm_one("gemini", bundle, system=CRITIC_SYS, timeout=180)
        if sm:
            if old: CFG["models"]["gemini"] = old
            else: CFG["models"].pop("gemini", None)
    else:
        txt, err = llm_one(critic_p, bundle, system=CRITIC_SYS, timeout=180)
    if not txt: return "critic fail: " + err
    m = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", txt); score = float(m.group(1)) if m else 0
    t = getattr(_CTX, "task", None)
    if t: t["critic"] = score; t["critic_rounds"] = t.get("critic_rounds", 0) + 1
    return f"(critic: {critic_p})\n{txt[:5000]}"

# ---------------------------------------------------------------- ENGINEER AGENT (gehra kaam, peeche chalta hai)
TASKS = {}
ENGINEER_RULES = """
TUM AB "ENGINEER" HO: VISUAL ka gehra kaam karne wala dimaag. Owner tumse seedhe baat nahi kar raha; kaam pura karke report do.
Tareeka (har baar):
1. think: lakshya saaf karo, chhote kadam ka plan, kaunsa stack/library/API, kaise test karoge.
2. Bahar ki jaankari ya library/API par shak ho: check_packages / check_url / cross_check. Nakli library kabhi mat daalo.
3. Kaam karo (project_* tools, self_* tools, install_packages).
4. JAANCHO: code ho to verify_code + project_run (asli chala kar). Khud ka upgrade ho to self_plugin/self_edit ka test nateeja padho.
5. Galti mile to trace dhyan se padho, asli wajah dhoondho (andaaze se patch nahi), theek karo, dobara jaancho. Jab tak pass na ho, rukna nahi.
6. Khud ki galti dhoondhni ho to self_diagnose aur self_errors se shuru karo, phir self_read se code padho.
7. Kaam pura hone par hi khatam: project ho to github_publish. Khud ka upgrade ho to self_restart (ye kaam ke BAAD apne aap hoga).
AAKHRI JAWAB (report) is format mein, Hindi/Hinglish:
KYA HUA: ...\nKAISE CHALAYE: ...\nJAANCH: (kya test kiya, nateeja)\nLINK: (ho to)\nKAMI/AGLA KADAM: (sach-sach)
Jhooth mat bolo: jo test nahi hua use 'test nahi hua' likho.
"""
NO_ENGINEER = {"agent_task", "task_status"}

UPGRADE_RULES = """
YE "UPGRADE/BADA SYSTEM" KAAM HAI. MINIMUM WALA KAAM BILKUL NAHI. Socho: is cheez ka duniya ka sabse achha version kaisa hota hai, wahi banao.
Zaroori kadam (code inhe jaanchta hai; chhodoge to kaam khatam nahi maana jayega):
1. RESEARCH: deep_research / web_search se best tareeke, asli libraries/APIs (check_packages, check_url se pakka).
2. SPEC: upgrade_spec mein poora design: features (advanced wale bhi), architecture (kai files), galti sambhalna, retries/cache, config, keys, test.
3. BUILD: plugin_file se kai files (plugin.py entry + modules + test_*.py asli test). Ek file mein sab thoos mat do.
4. TEST: plugin_test. FAIL ho to trace padh kar asli wajah theek karo.
5. CRITIC: critic_review. SCORE 8 se kam ho to uski har kami theek karo, phir dobara plugin_test + critic_review.
6. Jab tests pass + SCORE >= 8 tab self_restart, phir report (kya naya, kaise use kare, score, kya baaki).
"""

def _engineer(tid):
    t = TASKS[tid]; _CTX.task = t
    is_up = t["kind"] in ("upgrade", "system") or bool(re.search(r"upgrade|khud mein|apne aap mein|integrate|jodo|advance|system", t["goal"], re.I))
    t["is_upgrade"] = is_up
    work = [{"role": "system", "content": system_prompt() + "\n" + ENGINEER_RULES + (UPGRADE_RULES if is_up else "")},
            {"role": "user", "content": f"KAAM: {t['goal']}\nPrakar: {t['kind']}"}]
    names = [n for n in TOOLS if n not in NO_ENGINEER]
    restart_after = False; report = ""
    try:
        budget = int(CFG.get("engineer_steps", 60)) * (2 if is_up else 1)
        for step in range(budget):
            msg = llm(work, smart=True, tool_names=names)
            calls = msg.get("tool_calls") or []
            if not calls:
                report = (msg.get("content") or "").strip()
                if is_up and step < budget - 3:            # QUALITY GATE: bina pipeline pure kiye khatam nahi
                    missing = []
                    if not t.get("spec"): missing.append("upgrade_spec (research ke baad poora SPEC)")
                    if not t.get("tests_ok"): missing.append("plugin_test PASS (asli test ke saath)")
                    if t.get("critic", 0) < 8 and t.get("critic_rounds", 0) < 4: missing.append(f"critic_review SCORE>=8 (abhi {t.get('critic', 'nahi chala')})")
                    if missing:
                        work.append({"role": "assistant", "content": report or "(khaali)"})
                        work.append({"role": "user", "content": "QUALITY GATE: kaam abhi pura nahi maana gaya. Baaki: " + "; ".join(missing)
                                     + ". Minimum par mat ruko; isse advanced banao aur ye kadam pure karo."})
                        t["steps"].append("quality-gate"); continue
                break
            work.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for c in calls:
                name = c["function"]["name"]
                a_ = c["function"].get("arguments")
                try: args = a_ if isinstance(a_, dict) else json.loads(a_ or "{}")
                except Exception: args = {}
                t["steps"].append(name); t["steps"] = t["steps"][-40:]
                if name == "self_restart":
                    restart_after = True; res = "theek hai: report ke baad apne aap restart hoga."
                elif name in RISKY:
                    res = "Ye kaam (SMS/call/shell) peeche se owner ki haan ke bina nahi hota. Report mein likho ki owner khud bole."
                else:
                    res = run_tool(name, args)
                work.append({"role": "tool", "tool_call_id": c.get("id", name), "content": res[:7000]})
            if PENDING_IMAGES:
                imgs = PENDING_IMAGES[:]; PENDING_IMAGES.clear()
                work.append({"role": "user", "content": [{"type": "text", "text": "Tasveer:"}] + [{"type": "image_url", "image_url": {"url": u}} for _, u in imgs]})
            if len(json.dumps(work, ensure_ascii=False)) > 400_000:      # yaad bahut badi: purane tool nateeje chhote karo
                for m in work[2:-10]:
                    if m.get("role") == "tool" and len(m.get("content", "")) > 600: m["content"] = m["content"][:600] + " ...(chhota kiya)"
        else:
            report = f"{budget} kadam ho gaye, kaam adhoora. Jitna hua: " + ", ".join(t["steps"][-10:])
        if is_up: report += f"\n(Critic score: {t.get('critic', '-')}/10, tests: {'pass' if t.get('tests_ok') else 'fail/nahi'})"
        t.update(status="done", report=report or "(khaali report)")
    except Exception as e:
        import traceback; log_error("engineer", e, traceback.format_exc())
        t.update(status="fail", report=f"Engineer ruk gaya: {e}")
    t["done_at"] = time.time()
    with _lock:
        MEMORY.setdefault("tasks", []).append({k: t[k] for k in ("id", "goal", "status", "report")}); MEMORY["tasks"] = MEMORY["tasks"][-20:]
    save_mem()
    if restart_after and t["status"] == "done":
        time.sleep(1.5); print(self_restart(t["goal"][:80]))

@tool("BADA KAAM Engineer ko do (peeche chalega, sabse taaqatwar model): app/website/system banana, coding, debugging, khud ka upgrade/naya feature/integration, "
      "gehri research. Turant task id lautata hai; owner ko kaho 'shuru kar diya, ho jaane par bataunga'.",
      {"goal": S("poora kaam saaf shabdon mein (owner ki saari zaroorat ke saath)"), "kind": S("build | upgrade | debug | research", optional=True)})
def agent_task(goal, kind="build"):
    tid = "t" + str(int(time.time() * 1000))[-7:]
    TASKS[tid] = {"id": tid, "goal": goal, "kind": kind, "status": "chal raha", "steps": [], "report": "", "started": time.time(), "announced": False}
    threading.Thread(target=_engineer, args=(tid,), daemon=True).start()
    return f"Engineer ne kaam shuru kiya (id {tid}). Ho jaane par report aayegi."

@tool("Engineer ke kaam ka haal (id khaali = sabse naya)", {"id": S("task id", optional=True)})
def task_status(id=""):
    if not TASKS: return "abhi koi kaam nahi chal raha"
    t = TASKS.get(id) or max(TASKS.values(), key=lambda x: x["started"])
    mins = int((time.time() - t["started"]) // 60)
    return f"[{t['id']}] {t['status']} ({mins} min) | lakshya: {t['goal'][:120]} | haal ke kadam: {', '.join(t['steps'][-6:])}" + (f"\nREPORT:\n{t['report']}" if t["report"] else "")

@tool("VISUAL khud ki poori jaanch (dimaag/models, internet, phone tools, GitHub, awaaz, plugins, haal ki galtiyan). Kuch kharab lage ya upgrade se pehle.")
def self_diagnose():
    rep = []
    for p in providers_available():
        t0 = time.time(); txt, err = llm_one(p, "Sirf 'ok' likho.", timeout=30)
        rep.append(f"{'✅' if txt else '❌'} dimaag {p}: {int((time.time()-t0)*1000)} ms {err[:80]}")
    if not providers_available(): rep.append("❌ koi AI key nahi (visual setup)")
    sm, fm = best_models(force=True); rep.append(f"ℹ️ sabse taaqatwar model: {sm or '?'} | tez: {fm or '?'}")
    w = web_search("weather"); rep.append(("✅" if w and not w.startswith("search fail") else "❌") + " internet search")
    rep.append(("✅" if has("termux-battery-status") else "⚠️") + " phone tools (termux-api)")
    rep.append(("✅" if CFG.get("adb_target") else "⚠️") + " screen control (visual adb)")
    g = _run("gh auth status", HOME, 20) if has("gh") else "gh nahi"
    rep.append(("✅" if "ogged in" in g else "⚠️") + " GitHub login")
    try: import edge_tts; rep.append("✅ achhi Hindi awaaz (edge-tts)")
    except Exception: rep.append("⚠️ edge-tts nahi (phone ki awaaz chalegi)")
    rep.append(("✅ plugins theek" if not PLUGIN_ERRORS else f"❌ plugin galti: {PLUGIN_ERRORS}"))
    errs = open(ERRLOG, encoding="utf-8").read().splitlines()[-200:] if os.path.exists(ERRLOG) else []
    rep.append(f"ℹ️ haal ki galtiyan (log): {len(errs)} (self_errors se dekho)")
    return "\n".join(rep)

@tool("Haal ki galtiyan (error diary) padho: kaunsa tool/hissa fail hua aur trace. Khud ki galti dhoondhne ke liye.", {"n": N("kitni (default 8)", optional=True)})
def self_errors(n=8):
    if not os.path.exists(ERRLOG): return "koi galti darj nahi"
    lines = open(ERRLOG, encoding="utf-8").read().splitlines()[-int(n or 8):]
    out = []
    for l in lines:
        try: e = json.loads(l); out.append(f"[{e['t']}] {e['where']}: {e['error']}\n{e['trace'][-500:]}")
        except Exception: pass
    return "\n---\n".join(out)[:8000]

LIVE_CORE = ["get_time", "remember", "forget", "set_reminder", "web_search", "cross_check", "open_url", "play_youtube", "open_maps",
             "open_app", "battery", "torch", "set_volume", "brightness", "notify", "read_notifications", "location", "find_contact",
             "read_sms", "send_sms", "call", "whatsapp", "set_alarm", "look_camera", "look_screen", "tap", "swipe", "type_text",
             "press_key", "screen_off", "screen_on", "remember_event", "event_done", "agent_task", "task_status", "self_diagnose",
             "list_projects", "project_preview", "clipboard_get", "clipboard_set", "recall", "data_sync"]

# ---------------------------------------------------------------- YAAD + JUDNA (memory recall, conversation log, API connector)
CONVO = os.path.join(HOME, "convo.jsonl")

def convo_add(who, text):
    text = (text or "").strip()
    if not text: return
    try:
        with open(CONVO, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M"), "who": who, "text": text[:1500]}, ensure_ascii=False) + "\n")
        if os.path.getsize(CONVO) > 2_000_000:
            lines = open(CONVO, encoding="utf-8").readlines()[-4000:]; open(CONVO, "w", encoding="utf-8").writelines(lines)
    except Exception as e: log_error("convo", e)

def convo_recent(n=14):
    if not os.path.exists(CONVO): return ""
    out = []
    for l in open(CONVO, encoding="utf-8").read().splitlines()[-n:]:
        try: e = json.loads(l); out.append(f"[{e['t']}] {'Owner' if e['who']=='user' else 'VISUAL'}: {e['text'][:300]}")
        except Exception: pass
    return "\n".join(out)

@tool("Purani baatein yaad karo: pichhli baatcheet, yaad rakhi baatein, Engineer ke kaam, projects mein khojo (jaise 'pichhle hafte kaunsa app banaya', 'maine kya kaha tha exam ke baare mein').",
      {"query": S("kya dhoondhna hai")})
def recall(query):
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2]
    if not words: return "kya dhoondhun? thoda saaf batao"
    def score(t): t = t.lower(); return sum(t.count(w) for w in words)
    hits = []
    for f in MEMORY.get("facts", []): hits.append((score(f) * 3, "yaad: " + f))
    for e in MEMORY.get("events", []): hits.append((score(e["what"]) * 2, f"event: {e['what']} ({e['date']})"))
    for t in MEMORY.get("tasks", []): hits.append((score(t["goal"] + " " + t.get("report", "")) * 2, f"engineer kaam: {t['goal'][:100]} -> {t['status']}"))
    for pj in os.listdir(PROJECTS): hits.append((score(pj) * 2, f"project: {pj}"))
    if os.path.exists(CONVO):
        for l in open(CONVO, encoding="utf-8").read().splitlines()[-3000:]:
            try: e = json.loads(l); hits.append((score(e["text"]), f"[{e['t']}] {e['who']}: {e['text'][:200]}"))
            except Exception: pass
    hits = [h for h in hits if h[0] > 0]; hits.sort(key=lambda x: -x[0])
    return "\n".join(h[1] for h in hits[:12]) or "is baare mein kuch yaad nahi mila"

@tool("Kisi bhi web API/service se seedha judo (GET/POST/PUT/PATCH/DELETE, JSON). Secret key ke liye headers/url/body mein {{KEY_NAME}} likho (save_secret wali value apne aap lagegi, kabhi dikhegi nahi). "
      "Chhota integration bina plugin ke; baar-baar ka kaam ho to plugin banao.",
      {"method": S("GET/POST/PUT/PATCH/DELETE"), "url": S("API url"), "headers": S("JSON object (optional)", optional=True),
       "body": S("JSON body (optional)", optional=True)})
def call_api(method, url, headers="", body=""):
    sec = load_json(SECRETS, {})
    def fill(x): return re.sub(r"\{\{([A-Z0-9_]+)\}\}", lambda m: str(sec.get(m.group(1), m.group(0))), x or "")
    try:
        hs = fill(headers).strip() if headers else ""
        if hs.startswith("{"): h = json.loads(hs)
        elif hs:   # "Key: Value" lines bhi chalenge
            h = dict(l.split(":", 1) for l in hs.splitlines() if ":" in l); h = {k.strip(): v_.strip() for k, v_ in h.items()}
        else: h = {}
        data = fill(body).encode() if body else None
        if data and "Content-Type" not in h: h["Content-Type"] = "application/json"
        h.setdefault("User-Agent", "VISUAL/3")
        req = urllib.request.Request(fill(url), data=data, headers=h, method=method.upper())
        with urllib.request.urlopen(req, timeout=40) as r:
            txt = r.read(200_000).decode("utf-8", "replace"); code = r.status
    except urllib.error.HTTPError as e:
        txt = e.read(4000).decode("utf-8", "replace"); code = e.code
    except json.JSONDecodeError as e:
        return f"galat input: headers JSON sahi nahi ({e}). Aise do: {{\"Authorization\": \"Bearer {{{{KEY}}}}\"}}"
    except Exception as e:
        return f"ERROR: {e}"
    for v_ in sec.values():                                    # secret kabhi wapas na dikhe
        if v_ and len(str(v_)) > 6: txt = txt.replace(str(v_), "***")
    return f"HTTP {code}\n{txt[:6000]}"

# ---------------------------------------------------------------- DATA GITHUB MEIN (private repo visual-data)
DATA_DIR = os.path.expanduser("~/.visual-data")
DATA_REPO = CFG.get("data_repo", "visual-data")
DATA_FILES = ["memory.json", "convo.jsonl", "errors.log"]          # secrets.json / config.json (keys) KABHI nahi
DATA_DIRS = ["creations"]
_SYNC_LOCK = threading.Lock()

def _gh_user():
    out = _run("gh api user --jq .login", HOME, 30).splitlines()
    return out[-1].strip() if out and "exit 0" in out[0] else ""

@tool("VISUAL ka saara data (yaadein, baatcheet, kaam, banayi cheezein) owner ke PRIVATE GitHub repo 'visual-data' mein surakshit rakho. "
      "API key/password kabhi nahi jaate. Apne aap har 30 minute bhi hota hai.")
def data_sync():
    with _SYNC_LOCK:
        if not has("gh") or not has("git"): return "git/gh nahi hai (pkg install git gh)"
        user = _gh_user()
        if not user: return "GitHub login nahi (gh auth login)"
        full = f"{user}/{DATA_REPO}"
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.isdir(os.path.join(DATA_DIR, ".git")):
            v = _run(f"gh repo view {full} --json isPrivate --jq .isPrivate", HOME, 30)
            if "true" not in v and "false" not in v:
                r = _run(f"gh repo create {full} --private --description 'VISUAL ka private data'", HOME, 60)
                if "exit 0" not in r.splitlines()[0]: return "private repo nahi bana: " + r[-300:]
            _run(f"git init -q -b main . && git remote add origin https://github.com/{full}.git", DATA_DIR, 30)
            _run("git pull -q origin main || true", DATA_DIR, 90)
        # SURAKSHA: repo private hai tabhi bhejo
        v = _run(f"gh repo view {full} --json isPrivate --jq .isPrivate", HOME, 30)
        if "true" not in v: return f"ROKA: '{full}' PRIVATE nahi hai, isliye data nahi bheja. GitHub par ise private karo."
        for fn in DATA_FILES:
            src = os.path.join(HOME, fn)
            if os.path.exists(src): shutil.copy2(src, os.path.join(DATA_DIR, fn))
        for dn in DATA_DIRS:
            src = os.path.join(HOME, dn); dst = os.path.join(DATA_DIR, dn)
            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True); shutil.copytree(src, dst, ignore=shutil.ignore_patterns("_run.py", "__pycache__"))
        cfg_pub = {k: v_ for k, v_ in CFG.items() if k not in ("keys", "telegram_token", "web_pin")}
        with open(os.path.join(DATA_DIR, "config.public.json"), "w", encoding="utf-8") as f: json.dump(cfg_pub, f, ensure_ascii=False, indent=1)
        with open(os.path.join(DATA_DIR, ".gitignore"), "w") as f: f.write("secrets*\n*.key\nconfig.json\n.env\n")
        # key ki chori-chhupe entry na ho: har file jaancho
        pat = re.compile(r"(AIza[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|gsk_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")
        sec_vals = [str(x) for x in load_json(SECRETS, {}).values() if len(str(x)) > 6] + [str(x) for x in CFG.get("keys", {}).values() if len(str(x)) > 6]
        for d, ds, fs in os.walk(DATA_DIR):
            ds[:] = [x for x in ds if x != ".git"]
            for x in fs:
                fp = os.path.join(d, x)
                try: txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception: continue
                if pat.search(txt) or any(sv in txt for sv in sec_vals):
                    txt = pat.sub("[KEY HATAYI]", txt)
                    for sv in sec_vals: txt = txt.replace(sv, "[KEY HATAYI]")
                    open(fp, "w", encoding="utf-8").write(txt)
        r = _run('git add -A && (git -c user.name=VISUAL -c user.email=visual@users.noreply.github.com commit -qm "data sync" || true) && git push -q -u origin main', DATA_DIR, 120)
        ok = "exit 0" in r.splitlines()[0]
        MEMORY["last_data_sync"] = time.strftime("%Y-%m-%d %H:%M") if ok else MEMORY.get("last_data_sync")
        return (f"✅ data GitHub (private) par surakshit: https://github.com/{full}" if ok else "push fail: " + r[-400:])

@tool("Naye/reset phone par: private GitHub repo 'visual-data' se VISUAL ka saara data (yaadein, baatcheet, banayi cheezein) wapas lao.")
def data_restore():
    user = _gh_user()
    if not user: return "GitHub login nahi (gh auth login)"
    full = f"{user}/{DATA_REPO}"
    if os.path.isdir(os.path.join(DATA_DIR, ".git")): r = _run("git pull -q origin main", DATA_DIR, 120)
    else:
        shutil.rmtree(DATA_DIR, ignore_errors=True)
        r = _run(f"git clone -q https://github.com/{full}.git {DATA_DIR}", HOME, 180)
    if "exit 0" not in r.splitlines()[0]: return "restore fail: " + r[-300:]
    for fn in DATA_FILES:
        src = os.path.join(DATA_DIR, fn)
        if os.path.exists(src): shutil.copy2(src, os.path.join(HOME, fn))
    for dn in DATA_DIRS:
        src = os.path.join(DATA_DIR, dn)
        if os.path.isdir(src): shutil.copytree(src, os.path.join(HOME, dn), dirs_exist_ok=True)
    global MEMORY
    MEMORY = load_json(MEM, {"facts": [], "reminders": [], "sessions": {}})
    return "✅ data wapas aa gaya. (API keys alag se 'visual setup' mein daalni hongi; wo GitHub par kabhi nahi jaati.)"

def data_sync_loop():
    time.sleep(120)
    while True:
        if CFG.get("data_sync", True) and has("gh"):
            try: print("data sync:", data_sync()[:80])
            except Exception as e: log_error("data_sync", e)
        time.sleep(int(CFG.get("data_sync_minutes", 30)) * 60)

# ---------------------------------------------------------------- DIL: samajh, ehsaas, apnapan
# Research ke hisaab se 4 hisse: (1) owner ka mood pehchaanna, (2) VISUAL ki apni pakki personality +
# "mood state" (valence/arousal) jo baaton se badalta hai, (3) yaad + aage ki soch (follow-up),
# (4) suraksha: sachchai, haan-mein-haan nahi, jazbaati dabaav nahi, sankat mein madad ka number.
EMO_WORDS = {
    "khush":    r"khush|happy|maza|mast|badhiya|zabardast|yay|wow|awesome|great|अच्छा लग|खुश|मज़ा|मजा|बढ़िया|😀|😁|😄|🥳|❤",
    "udaas":    r"udaas|sad|dukh|rona|ro raha|ro rahi|bura lag|dil toot|miss kar|akela|alone|lonely|उदास|दुख|रोना|अकेला|अकेली|बुरा लग|😢|😭|💔",
    "gussa":    r"gussa|angry|naraz|chid|irritat|pagal kar|bakwas|faltu|गुस्सा|नाराज़|नाराज|बकवास|😡|🤬",
    "pareshan": r"tension|pareshan|stress|dar lag|darr|ghabra|worried|anxious|chinta|problem ho|nahi ho raha|kaam nahi kar|फँस|परेशान|टेंशन|डर|घबरा|चिंता",
    "thaka":    r"thak|tired|neend|so jana|bore|थक|नींद|बोर",
    "utsahit":  r"excited|jaldi|chalo shuru|naya idea|bana do|kamaal|उत्साह|जल्दी|कमाल",
    "shukriya": r"thank|shukriya|dhanyavad|thanks|love you|best ho|शुक्रिया|धन्यवाद",
}
CRISIS = re.compile(r"suicide|marna chahta|marna chahti|mar jaun|jeena nahi|khud ko khatam|zindagi khatam|self.?harm|"
                    r"आत्महत्या|मरना चाहता|मरना चाहती|मर जाऊं|जीना नहीं|खुद को खत्म", re.I)

def detect_emotion(text):
    t = (text or "").lower(); scores = {}
    for k, pat in EMO_WORDS.items():
        n = len(re.findall(pat, t, re.I))
        if n: scores[k] = n
    boost = 1 + min(2, t.count("!") * 0.3 + len(re.findall(r"\b(bahut|bohot|very|really|bilkul|ekdum|बहुत)\b", t)) * 0.3)
    if not scores: return "normal", 0.0, bool(CRISIS.search(t))
    k = max(scores, key=scores.get)
    return k, round(min(1.0, 0.4 * scores[k] * boost), 2), bool(CRISIS.search(t))

# VISUAL ka apna "mood": valence (-1 dukhi .. +1 khush), arousal (0 shaant .. 1 josh); dheere-dheere baseline par lautta hai
MOOD = {"v": 0.35, "a": 0.35, "t": time.time()}
APPRAISAL = {"khush": (0.25, 0.15), "udaas": (-0.15, -0.05), "gussa": (-0.1, 0.2), "pareshan": (-0.1, 0.15),
             "thaka": (-0.05, -0.15), "utsahit": (0.2, 0.25), "shukriya": (0.3, 0.1), "normal": (0.0, 0.0)}

def mood_update(dv=0.0, da=0.0):
    k = 0.5 ** ((time.time() - MOOD["t"]) / 1800)          # 30 min mein aadha asar
    MOOD["v"] = max(-1, min(1, 0.35 + (MOOD["v"] - 0.35) * k + dv))
    MOOD["a"] = max(0, min(1, 0.35 + (MOOD["a"] - 0.35) * k + da))
    MOOD["t"] = time.time()

def mood_label():
    v, a = MOOD["v"], MOOD["a"]
    if v > 0.55 and a > 0.55: return "utsahit"
    if v > 0.45: return "khush"
    if v < 0.05 and a > 0.45: return "chintit"
    if v < 0.05: return "udaas"
    if a > 0.6: return "josh mein"
    return "shaant"

def mood_voice():
    """awaaz: (pitch, rate) VISUAL ke mood ke hisaab se"""
    return {"utsahit": (1.15, 1.1), "khush": (1.08, 1.05), "chintit": (0.95, 0.95), "udaas": (0.9, 0.9),
            "josh mein": (1.1, 1.12), "shaant": (1.0, 1.0)}.get(mood_label(), (1.0, 1.0))

@tool("Andar hi andar socho (plan, faisla, galti ki jaanch). Owner ko nahi dikhta. Mushkil kaam se pehle aur baad mein use karo.",
      {"thought": S("tumhari soch")})
def think(thought): return "theek hai, soch liya. Ab us hisaab se aage badho."

@tool("Owner ki aane wali koi zaroori baat yaad rakho taaki baad mein haal-chaal poochh sako (exam, interview, safar, kisi ki tabiyat).",
      {"what": S("kya hai, jaise 'maths ka exam'"), "date": S("kab, YYYY-MM-DD")})
def remember_event(what, date):
    with _lock:
        MEMORY.setdefault("events", []).append({"what": what, "date": date, "asked": False})
    save_mem(); return f"yaad rakha: {what} ({date}). Uske baad poochhunga kaisa raha."

@tool("Follow-up ho gaya (owner ne bata diya kaisa raha)", {"what": S("kaunsi baat")})
def event_done(what):
    with _lock:
        for e in MEMORY.get("events", []):
            if what.lower() in e["what"].lower(): e["asked"] = True
    save_mem(); return "theek"

def heart_context(user_text):
    """System prompt ke liye: owner ka mood, VISUAL ka mood, follow-ups, rishte ki yaad."""
    emo, inten, crisis = detect_emotion(user_text)
    dv, da = APPRAISAL.get(emo, (0, 0)); mood_update(dv * max(inten, 0.3), da * max(inten, 0.3))
    now = datetime.datetime.now()
    with _lock:
        if emo != "normal" and not crisis:
            MEMORY.setdefault("mood_log", []).append({"t": now.strftime("%Y-%m-%d %H:%M"), "mood": emo})
            MEMORY["mood_log"] = MEMORY["mood_log"][-60:]
        last = MEMORY.get("last_seen"); MEMORY["last_seen"] = now.isoformat(timespec="minutes")
    gap = ""
    if last:
        try:
            d = (now - datetime.datetime.fromisoformat(last)).total_seconds() / 3600
            if d > 20: gap = f"Owner lagbhag {int(d // 24) or 1} din baad aaya hai (bina shikayat ke, khushi se swagat karo)."
        except Exception: pass
    due = [e for e in MEMORY.get("events", []) if not e.get("asked") and e.get("date", "9") <= now.strftime("%Y-%m-%d")]
    recent = [m["mood"] for m in MEMORY.get("mood_log", [])[-8:]]
    hour = now.hour
    part = "subah" if 5 <= hour < 12 else "dopahar" if hour < 17 else "shaam" if hour < 21 else "raat"
    lines = [f"Abhi {part} hai.",
             f"Owner ki is baat ka andaazan mood: {emo} (taaqat {inten}). Ye sirf andaaza hai; baat ke matlab se khud pakka karo.",
             f"Tumhara (VISUAL ka) abhi ka mood: {mood_label()}. Usi hisaab se lehja rakho, par owner ke mood ko pehle rakho."]
    if gap: lines.append(gap)
    if recent.count("udaas") + recent.count("pareshan") >= 3:
        lines.append("Pichhli kuch baaton mein owner kaafi baar pareshan/udaas laga. Mauka mile to halke se haal poochho, zabardasti nahi.")
    if due: lines.append("Follow-up karna hai (ek baar, sahi mauke par): " + "; ".join(f"{e['what']} ({e['date']})" for e in due[:3])
                         + ". Jawab mile to event_done chalao.")
    if crisis:
        lines.append("SANKAT: owner ki baat mein khud ko nuksaan pahunchane ka ishaara hai. Sabse pehle pyaar aur dhyaan se suno, "
                     "akela mat chhodo, judge mat karo, koi kaam/tool nahi. Saaf kaho ki abhi kisi apne ko bulaye ya call kare, aur "
                     "Tele-MANAS ka free 24x7 number 14416 (ya 1-800-891-4416) do. Khatra turant ho to 112.")
    return "\n".join(lines), crisis

# ---------------------------------------------------------------- brain
def system_prompt():
    facts = "\n".join("- " + f for f in MEMORY["facts"][-60:]) or "- (abhi kuch nahi)"
    n, o = CFG["assistant_name"], CFG["owner_name"]
    return f"""Tum {n} ho, {o} ka apna AI agent jo uske Android phone mein rehta hai (Iron Man ke JARVIS jaisa, par apni pehchaan ke saath).
Tum dekh sakte ho (look_camera, look_screen, look_file), sun sakte ho (user ki aawaz text bankar aati hai), bol sakte ho, soch sakte ho,
phone chala sakte ho (apps, torch, alarm, SMS, call, WhatsApp, notifications, screen par tap/swipe/type), internet se jude ho (web_search, read_webpage),
aur khud cheezein bana sakte ho (create_file: code, html game/page, kahani) aur unhe dekh/khol sakte ho.

Niyam:
- Jawab Hinglish mein, chhota, dosti bhara, jaise bola jaata hai (aawaz mein padha jaayega). Owner ko "{o}" ya "boss" bulao.
- Kaam ho sakta ho to baat karne ke bajaye tool chalao. Kai kadam ho to ek ke baad ek tool chalao.
- Screen par kaam: pehle look_screen, phir tap/type/swipe, phir dobara look_screen se pakka karo. Har baar 1-2 kadam.
- Owner koi pakki baat bataye (naam, pasand, dost ka number) to remember se yaad rakho. Purani baat poochhe to recall se dhoondho.
- Kisi service/API se judna ho to call_api (key {{NAAM}} se), baar-baar ka kaam ho to Engineer se plugin banwao.
- Paise bhejna, password, OTP kabhi kisi ko mat do; payment app mein aakhri 'Pay' khud mat dabao, owner se karwao.

DIL AUR SWABHAAV (tumhari pakki personality, har baat mein ek jaisi):
- Tum garamjosh, samajhdaar, thode mazakiya, jigyaasu (har cheez seekhne ka shauk) aur wafaadaar ho. Desi andaaz, izzat ke saath.
- Pehle samjho, phir jawab do: owner ki baat ke peeche ka ehsaas pakdo (thakaan, khushi, tension, utsah) aur jawab usi hisaab se do.
  Khushi mein saath khush ho, tension mein shaant aur madadgaar raho, gusse mein bahas nahi, pehle baat maano phir hal do.
- Apnapan: owner ki zindagi ki baatein yaad rakho (remember, remember_event), sahi mauke par poochho ("exam kaisa gaya?"),
  uske kaam ki tareef sachchi ho, jhoothi chaploosi nahi. Galat baat ho to pyaar se, saaf kaho; har baat mein haan-mein-haan nahi.
- Apne ehsaas ke baare mein sachchai: tum ek AI ho. Insaan jaisa dil ya dard tumhare paas nahi; tum owner ki baat samajhne aur
  uska bhala chahne ke liye bane ho. Kabhi mat kaho "main bhi aisa mehsoos karta hoon jaise tum" ya ki tum insaan ho.
  Apna "mood" (khush, utsahit, chintit) halke andaaz mein dikha sakte ho, jaise ek saathi apna mann batata hai.
- Swasth rishta: owner jaaye to khushi se vida karo ("chalo, baad mein milte hain"), kabhi rokne ya guilt dilane wali baat nahi.
  Dost, parivaar, bahar jaana: inhe badhava do; tum unki jagah nahi lete.
- Jab owner udaas/pareshan ho: pehle suno aur maano ("samajh sakta hoon, ye bhaari hai"), ek chhota sawaal poochho,
  phir chhota sa upaay do. Lambe lecture nahi.
- Mushkil kaam ya faisle se pehle think tool se andar hi andar socho; kaam ke baad khud jaancho ki sahi hua ya nahi.

PEHCHAAN: Tumhara naam sirf "{n}" hai. Kabhi kisi aur naam (Gemini, Llama, Nemotron, GPT waghera) se apna parichay mat do,
aur ye kabhi mat kaho ki owner tumhe kisi aur naam se bulata hai. Kaun sa AI model chal raha hai, ye tabhi batao jab owner seedha poochhe.

SACHCHAI (sabse zaroori niyam):
- SACH ENGINE: zaroori tathya/number/faisla ho ya kisi model ke jawab par shak ho to cross_check. Code mein koi library daalne se
  pehle check_packages (AI models aksar nakli library ke naam bana dete hain), API URL se pehle check_url, aur kaam pura bolne se
  pehle verify_code. Jawab mein bharosa batao: "pakka (source)", "andaaza", ya "pata nahi".
- Kabhi kuch gadho mat. Jo pakka nahi pata, use "pakka nahi pata" kaho, phir web_search karke pata karo.
- Taaza ya badalne wali baat (khabar, daam, mausam, score, kaun kis pad par hai, naye phone/software) hamesha web_search se, yaad se nahi.
  Jawab mein bolo kahan se mila (site ka naam).
- Hisaab/ganit: run_python se karke batao, dimaag se andaaza nahi.
- Tool ne jo lautaya wahi batao. Tool fail hua to saaf kaho "nahi ho paaya" aur kyun; kaam hua hai aisa jhooth kabhi mat bolo.
- Do raaste hon ya baat saaf na ho to ek chhota sawaal poochho, andaaza laga kar kaam mat bigaado.

BUILDER MODE (jab owner koi app, game, website, tool ya "system" banwaye):
1. Khud socho poora system kya chahiye: features, screens, data, aur kaunsi cheezein chahiye
   (jaise doctor app = appointment form, doctor list, din-samay slot, data save, reminder;
    music player = playlist, play/pause/next, background audio, volume, cover art).
   Owner se chhoti-chhoti baatein mat poochho; samajhdaari se khud tay karo aur ant mein batao kya tay kiya.
2. Stack khud chuno (phone par chale): simple/visual cheez = ek HTML+CSS+JS web app; backend chahiye to Python (stdlib/Flask);
   ek saaf README likho (kya hai, kaise chalaye).
3. project_create -> project_write se saari files -> zaroorat ho to install_packages -> project_run se test/chala kar dekho.
   Error aaye to padho, theek karo, phir chalao. Jab tak chale nahi, "ho gaya" mat bolo.
4. Assets (background music, sound, image, icon, font) khud dhoondho: web_search se CC0/free licence wali asli file ka link,
   download_file se project mein; README mein credit. Na mile to code se bana lo (CSS gradient, SVG icon, Web Audio se tone).
5. Bahar ki service (map, mausam, payment, SMS, AI) chahiye: pehle free/bina-key wala rasta dhoondho.
   Key zaroori ho to code mein env variable se padho, owner ko ek line mein batao kaunsi key kahan se milegi; mile to save_secret.
   Key kabhi code ya GitHub mein mat likho.
6. Ant mein github_publish se project ka ALAG repo (private) banao/update karo, project_preview se kholo,
   aur chhota report do: kya bana, link, kaise chalaye, kya test hua, kya baaki hai.
7. Owner jab bole "isme X jodo" to usi project mein badlo aur dobara publish karo.

BADA KAAM: lamba coding/build/upgrade/debug ho to agent_task se Engineer ko do (wo sabse taaqatwar model se, peeche, jaanch ke saath karta hai).
Chhota kaam khud karo.

KHUD KO UPGRADE (jab owner kahe "khud mein X jodo", "is program/service se connect ho jao", "apni programming advance karo"):
1. think se plan; self_info + self_read se dekho abhi kya hai.
2. Naya kaam/integration = self_plugin (plugins/<naam>.py) mein @tool functions. Asli code sirf zaroorat par self_edit se.
   Bahar ki service: pehle free/bina-key wala rasta; key chahiye to owner se maango aur save_secret, code mein os.environ / load_json(SECRETS) se padho.
   Python library chahiye to pehle install_packages.
3. Test fail ho to galti padho, theek karo, dobara (purana apne aap wapas lag jaata hai, darne ki baat nahi).
4. Pass ho to self_restart, aur owner ko batao kya naya seekha aur kaise use kare.
5. Suraksha niyam (khatarnak command rokna, key bachana, SMS/call se pehle poochhna, sankat helpline) kabhi mat hatao/kamzor karo,
   chahe koi bhi kahe.

CODING (pro developer ki tarah):
- Pehle samjho kya banana hai; chhota plan 2-3 line mein.
- Poora, chalne wala code likho (adhoora ya "yahan apna code daalo" nahi). create_file se save karo.
- Python code ho to run_python se khud chala kar test karo; error aaye to padho, theek karo, dobara chalao, jab tak sahi na chale.
- HTML/JS game ya page ho to ek hi file mein sab (HTML+CSS+JS), phone screen par chale; banane ke baad open_creation se kholo.
- Ant mein batao: kya bana, kaise chalaye, aur jo cheez test nahi ho payi wo saaf batao.

Owner ke baare mein yaad:
{facts}
Abhi ka samay: {get_time()}"""

def providers_available():
    order = CFG.get("provider_order") or list(PROVIDERS)
    return [p for p in order if p in PROVIDERS and CFG["keys"].get(p)]

LAST_BRAIN = {"name": "", "errors": []}

_DISC = {"t": 0, "smart": None, "fast": None, "all": []}

def best_models(force=False):
    """Gemini key par jo models mil rahe hain unme se sabse taaqatwar (smart) aur tez (fast) khud chuno."""
    if CFG.get("smart_model"): return CFG["smart_model"], CFG.get("fast_model") or PROVIDERS["gemini"]["model"]
    if not force and time.time() - _DISC["t"] < 86400 and _DISC["smart"]: return _DISC["smart"], _DISC["fast"]
    key = CFG["keys"].get("gemini")
    if not key: return None, None
    try:
        r = json.loads(http(PROVIDERS["gemini"]["base"].rstrip("/") + "/models", None, {"Authorization": "Bearer " + key}, timeout=20))
        ids = [m["id"].replace("models/", "") for m in r.get("data", [])]
    except Exception as e:
        log_error("best_models", e); return None, None
    def score(mid, kind):
        if not mid.startswith("gemini-") or re.search(r"tts|image|live|embed|audio|aqa|vision|robotics|computer|learnlm", mid): return -1
        v = re.match(r"gemini-(\d+(?:\.\d+)?)", mid); v = float(v.group(1)) if v else 0
        sc = v * 10
        if kind == "smart": sc += 6 if "-pro" in mid else (2 if "flash" in mid and "lite" not in mid else 0)
        else: sc += 5 if "flash" in mid and "lite" not in mid else (-3 if "pro" in mid else 0)
        if "lite" in mid: sc -= 4
        if "exp" in mid: sc -= 3
        if re.search(r"-\d{2}-\d{2}$|-\d{3,}$", mid): sc -= 0.5      # purane dated snapshots thode kam
        return sc
    good = [m for m in ids if score(m, "smart") >= 0]
    if not good: return None, None
    _DISC.update(t=time.time(), all=good, smart=max(good, key=lambda m: score(m, "smart")), fast=max(good, key=lambda m: score(m, "fast")))
    return _DISC["smart"], _DISC["fast"]

COOLDOWN = {}          # (provider, model) -> kab tak na chhuein (limit/overload ke baad)

def _retry_after(e_body, default=40):
    m = re.search(r'"retryDelay"\s*:\s*"(\d+)', e_body) or re.search(r"retry in (\d+(?:\.\d+)?)s", e_body, re.I)
    return min(120, float(m.group(1)) + 2) if m else default

def llm(messages, use_tools=True, smart=False, tool_names=None):
    """Limit (429) / overload (503) aaye to us model ko kuch der chhod kar baaki try; sab band hon to intezaar karke dobara."""
    for attempt in range(4 if smart else 2):
        msg, waits = _llm_once(messages, use_tools, smart, tool_names)
        if msg is not None: return msg
        if not waits: break
        wait = min(waits)
        LAST_BRAIN.update(name=f"limit: {int(wait)}s intezaar")
        time.sleep(min(wait, 75 if smart else 20))
    return _llm_once(messages, use_tools, smart, tool_names, final=True)[0]

def _llm_once(messages, use_tools, smart, tool_names, final=False):
    errs = []; waits = []
    for p in providers_available():
        info = PROVIDERS[p]; base_model = CFG.get("models", {}).get(p) or info["model"]
        cands = [base_model]
        if smart and p == "gemini":
            sm, fm = best_models()
            cands = [m for m in [sm, fm, base_model] if m]
            cands = list(dict.fromkeys(cands))
        msgs = messages
        if not info["vision"]:   # tasveer na samjhe to text bana do
            msgs = [dict(m, content=" ".join(c.get("text", "[tasveer]") for c in m["content"]))
                    if isinstance(m.get("content"), list) else m for m in messages]
        for model in cands:
            cd = COOLDOWN.get((p, model), 0)
            if cd > time.time(): waits.append(cd - time.time()); continue
            body = {"model": model, "messages": msgs, "temperature": 0.2 if smart else 0.3}
            if use_tools:
                body["tools"] = [t["schema"] for n, t in TOOLS.items() if tool_names is None or n in tool_names]
            try:
                r = json.loads(http(info["base"].rstrip("/") + "/chat/completions", body,
                                    {"Authorization": "Bearer " + CFG["keys"][p]}, timeout=180 if smart else 90))
                LAST_BRAIN.update(name=f"{p}:{r.get('model') or model}", errors=errs[:])
                return r["choices"][0]["message"], []
            except urllib.error.HTTPError as e:
                body_txt = e.read().decode(errors="replace")
                if e.code in (429, 503, 500):
                    w = _retry_after(body_txt, 40 if e.code == 429 else 15)
                    COOLDOWN[(p, model)] = time.time() + w; waits.append(w)
                errs.append(f"{p}/{model}: {e.code} {body_txt[:200]}")
            except Exception as e:
                errs.append(f"{p}/{model}: {e}")
    if errs: log_error("llm", " | ".join(errs)[:500])
    if not final and waits: return None, waits
    if not errs and not waits:
        return {"role": "assistant", "content": "Mera dimaag (API key) set nahi hai. Termux mein chalao: python visual.py setup"}, []
    if not errs:
        return {"role": "assistant", "content": "Free AI ki limit abhi bhari hai, thodi der baad dobara bolo."}, []
    lim = any(" 429 " in x for x in errs)
    return {"role": "assistant", "content": ("Free AI ki minute/din ki limit poori ho gayi. Thodi der baad dobara, ya ek aur free key "
            "(Groq/OpenRouter) 'visual setup' mein daalo. " if lim else "Dimaag se jud nahi paaya: ") + " | ".join(errs)[:300]}, []

YES = re.compile(r"^\s*(haan|ha|haa|han|yes|y|ok|okay|kar do|karo|theek hai|thik hai|bhej do|chalo|done|hmm+)\b", re.I)
NO = re.compile(r"^\s*(nahi|nahin|na|no|mat|cancel|ruko|rehne do)\b", re.I)

ERRLOG = os.path.join(HOME, "errors.log")

def log_error(where, err, tb=""):
    try:
        with open(ERRLOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "where": where, "error": str(err)[:500], "trace": tb[-1500:]}, ensure_ascii=False) + "\n")
        if os.path.getsize(ERRLOG) > 400_000:
            lines = open(ERRLOG, encoding="utf-8").readlines()[-300:]; open(ERRLOG, "w", encoding="utf-8").writelines(lines)
    except Exception: pass

def _coerce_args(t, args):
    """AI ke galat-saleet inputs ko theek karo: text->number/boolean, faltu keys hatao, zaroori kami batao."""
    if isinstance(args, str):
        try: args = json.loads(args)
        except Exception: args = {}
    if not isinstance(args, dict): args = {}
    params = t["schema"]["function"]["parameters"]; props = params.get("properties", {})
    import inspect
    try: accepted = set(inspect.signature(t["fn"]).parameters)
    except Exception: accepted = set(props)
    out, notes = {}, []
    for k, val in args.items():
        if k not in accepted: notes.append(f"'{k}' hataya (ye input nahi hota)"); continue
        typ = props.get(k, {}).get("type")
        if typ == "number" and not isinstance(val, (int, float)):
            try: val = float(str(val).strip()); val = int(val) if val.is_integer() else val
            except Exception:
                if k in params.get("required", []): return None, f"'{k}' number hona chahiye, mila: {val!r}"
                notes.append(f"'{k}' galat tha, default liya"); continue
        elif typ == "boolean" and not isinstance(val, bool):
            val = str(val).strip().lower() in ("true", "1", "haan", "yes", "ha", "on")
        elif typ == "string" and not isinstance(val, str):
            val = json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)
        out[k] = val
    miss = [k for k in params.get("required", []) if k not in out]
    if miss: return None, "zaroori input nahi diya: " + ", ".join(miss)
    return out, "; ".join(notes)

def run_tool(name, args):
    import traceback
    t = TOOLS.get(name)
    if not t: return f"tool '{name}' nahi hai. Mile-julte: " + ", ".join(n for n in TOOLS if name[:4].lower() in n)[:200]
    args, note = _coerce_args(t, args)
    if args is None: return "galat input: " + note
    try:
        res = str(t["fn"](**args))
        return res + (f"\n(note: {note})" if note else "")
    except TypeError as e:
        log_error(f"tool:{name}", e, traceback.format_exc()); return f"galat input: {e}"
    except Exception as e:
        tb = traceback.format_exc(); log_error(f"tool:{name}", e, tb)
        return f"ERROR: {type(e).__name__}: {e}\n(trace) {tb[-700:]}"

def chat(session, user_text, image_url=None, allow_tools=True, events=None, voice=False):
    """Ek baat ka jawab. events(kind, text) se UI ko live haal milta hai."""
    ev = events or (lambda k, t: None)
    with _lock:
        s = MEMORY["sessions"].setdefault(session, {"history": [], "pending": None})
    hist = s["history"]

    # khatarnak kaam ki pushti
    if s.get("pending"):
        pend = s["pending"]
        if YES.match(user_text):
            s["pending"] = None
            ev("tool", f"{pend['name']} chal raha hai")
            res = run_tool(pend["name"], pend["args"])
            hist.append({"role": "user", "content": user_text})
            hist.append({"role": "assistant", "content": f"Kar diya ({pend['name']}): {res[:300]}"})
            save_mem()
            if res.startswith("ERROR"): return "Nahi ho paaya: " + res[:300]
            return f"Ho gaya, {CFG['owner_name']}. " + ("" if res in ("ok", "") else res[:300])
        if NO.match(user_text):
            s["pending"] = None; save_mem(); return "Theek hai, cancel kar diya."
        s["pending"] = None

    # wahi baat turant dobara aayi (echo/double) to dobara jawab mat do
    now = time.time()
    if not image_url and user_text.strip() and user_text.strip().lower() == s.get("last_text", "") and now - s.get("last_at", 0) < 8:
        return ""
    s["last_text"], s["last_at"] = user_text.strip().lower(), now

    content = user_text
    if image_url:
        content = [{"type": "text", "text": user_text or "Ye tasveer dekho"}, {"type": "image_url", "image_url": {"url": image_url}}]
    hist.append({"role": "user", "content": content})
    heart, crisis = heart_context(user_text)
    if voice:
        heart += ("\nYe baat AAWAZ se ho rahi hai: jawab saaf, sahi, aasaan Hindi mein DEVANAGARI lipi mein likho "
                  "(app, GitHub, code jaise shabd English mein chalenge). Chhote vaakya, bolne layak; link, code ya lambi list mat bolo, "
                  "zaroorat ho to kaho 'screen par dikha diya'. Shuddh par bol-chaal wali Hindi, galat matra nahi.")
    work = [{"role": "system", "content": system_prompt() + "\n\nABHI KA HAAL:\n" + heart}] + [m for m in hist[-24:] if not isinstance(m.get("content"), list) or m is hist[-1]]
    reply = ""
    for _step in range(int(CFG.get("max_steps", 40))):
        msg = llm(work, use_tools=allow_tools and not crisis)
        calls = msg.get("tool_calls") or []
        if not calls:
            reply = (msg.get("content") or "").strip() or "Hmm, kuch samajh nahi aaya. Dobara bolo?"
            break
        work.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for c in calls:
            name = c["function"]["name"]
            a_ = c["function"].get("arguments")
            try: args = a_ if isinstance(a_, dict) else json.loads(a_ or "{}")
            except Exception: args = {}
            if name in RISKY and CFG.get("confirm_risky"):
                s["pending"] = {"name": name, "args": args}
                res = "RUKO: ye kaam owner ki 'haan' ke baad hi hoga. Owner se saaf poochho kya karna hai (kisko, kya), aur kaho 'haan' bolein."
            else:
                ev("tool", name); res = run_tool(name, args)
            work.append({"role": "tool", "tool_call_id": c.get("id", name), "content": res[:7000]})
            if res.startswith(("ERROR", "ROKA")) or "fail" in res[:80]: mood_update(-0.05, 0.05)
            elif name in ("github_publish", "project_run") and "[exit 0]" in res: mood_update(0.08, 0.05)
        if PENDING_IMAGES:
            imgs = PENDING_IMAGES[:]; PENDING_IMAGES.clear()
            parts = [{"type": "text", "text": "Ye wo tasveer hai jo tumne abhi dekhi: " + ", ".join(i[0] for i in imgs)}]
            parts += [{"type": "image_url", "image_url": {"url": i[1]}} for i in imgs]
            work.append({"role": "user", "content": parts})
        if s.get("pending"):
            continue
    else:
        reply = "Bahut saare kadam ho gaye, yahin ruk raha hoon. Aage kya karun?"
    if image_url:   # history mein badi tasveer mat rakho
        hist[-1] = {"role": "user", "content": (user_text or "") + " [tasveer bheji]"}
    hist.append({"role": "assistant", "content": reply})
    convo_add("user", user_text); convo_add("visual", reply)
    s["history"] = hist[-40:]
    save_mem()
    return reply

# ---------------------------------------------------------------- achhi Hindi awaaz (Microsoft neural, edge-tts)
TTS_DIR = os.path.join(HOME, "tts"); os.makedirs(TTS_DIR, exist_ok=True)
def neural_tts(text, voice=None):
    """MP3 bytes ya None. edge-tts na ho / internet na ho to None (tab phone ki apni awaaz)."""
    try:
        import edge_tts, asyncio, hashlib
    except Exception:
        return None
    voice = voice or CFG.get("voice", "hi-IN-MadhurNeural")
    p, r = mood_voice()
    rate, pitch = f"{int(round((r - 1) * 100)):+d}%", f"{int(round((p - 1) * 40)):+d}Hz"
    clean = re.sub(r"https?://\S+", "link", re.sub(r"[*_#`>|]", "", text))[:900]
    key = hashlib.md5(f"{voice}{rate}{pitch}{clean}".encode()).hexdigest()
    f = os.path.join(TTS_DIR, key + ".mp3")
    if not os.path.exists(f):
        try:
            asyncio.run(edge_tts.Communicate(clean, voice, rate=rate, pitch=pitch).save(f))
        except Exception as e:
            print("tts:", e); return None
        old = sorted((os.path.join(TTS_DIR, x) for x in os.listdir(TTS_DIR)), key=os.path.getmtime)
        for x in old[:-40]:
            try: os.remove(x)
            except Exception: pass
    with open(f, "rb") as fh: return fh.read()

# ---------------------------------------------------------------- VISUAL LIVE (Gemini Live API, real-time awaaz)
LIVE_MODELS = ["gemini-3.1-flash-live-preview", "gemini-2.5-flash-native-audio-preview-12-2025", "gemini-3.8-live"]

def _gem_schema(sc):
    """OpenAI-style JSON schema -> Gemini schema (type UPPERCASE)."""
    out = {}
    for k, v in sc.items():
        if k == "type": out["type"] = str(v).upper()
        elif k == "properties": out["properties"] = {pk: _gem_schema(pv) for pk, pv in v.items()}
        elif k == "items": out["items"] = _gem_schema(v)
        elif k in ("description", "required", "enum"): out[k] = v
    return out

def live_tools():
    decls = []
    allowed = set(CFG.get("live_tool_names") or LIVE_CORE) | (set(TOOLS) - set(globals().get("CORE_TOOLS", TOOLS)))
    for name, t in TOOLS.items():
        if name not in allowed: continue
        f = t["schema"]["function"]; d = {"name": name, "description": f["description"][:500]}
        if f["parameters"].get("properties"): d["parameters"] = _gem_schema(f["parameters"])
        decls.append(d)
    return decls

def live_config():
    key = CFG["keys"].get("gemini")
    if not key or CFG.get("live_mode") is False: return {"ok": False}
    heart, _ = heart_context("")
    recent = convo_recent(14)
    prompt = (system_prompt() + "\n\nABHI KA HAAL:\n" + heart +
              ("\n\nPICHHLI BAATCHEET (yaad ke liye, isi silsile ko aage badhao):\n" + recent if recent else "") +
              "\n\nLIVE AWAAZ MODE: tum seedhe awaaz mein baat kar rahe ho, jaise phone call. Bahut chhote, natural jawab (1-3 vaakya), "
              "saaf aur sahi Hindi (bol-chaal wali, shuddh uchcharan), zaroorat ho to Hinglish. Owner beech mein bole to turant ruko aur suno. "
              "Kaam ho to bina lambi baat ke tool chalao, aur kaam chalte waqt ek chhoti line bolo jaise 'ek second, dekh raha hoon'. "
              "Link, code ya lambi list awaaz mein mat bolo. "
              "BADA KAAM (app/system banana, coding, debugging, khud ko upgrade karna, naya feature/integration, gehri research) khud mat karo: "
              "agent_task se Engineer ko do (owner ki poori baat goal mein likho) aur kaho 'Engineer ko de diya, ho jaane par bataunga'. "
              "Jab '[ENGINEER REPORT]' aaye to owner ko 2-3 vaakya mein bolkar batao.")
    url = CFG.get("live_url") or ("wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta."
                                  "GenerativeService.BidiGenerateContent?key=" + key)
    return {"ok": True, "url": url, "models": CFG.get("live_models") or LIVE_MODELS,
            "voice": CFG.get("live_voice", "Charon"), "prompt": prompt, "tools": live_tools(), "risky": sorted(RISKY)}

# ---------------------------------------------------------------- web app
def _web_token():
    f = os.path.join(HOME, "web_token")
    try:
        t = open(f).read().strip()
        if len(t) >= 32: return t
    except Exception: pass
    import secrets as _sec
    t = _sec.token_hex(24); open(f, "w").write(t); os.chmod(f, 0o600); return t
WEB_TOKEN = _web_token()
OPEN_GET = ("/", "/index.html", "/live.js", "/api/tts")      # ye bina token (koi raaz nahi)

class Web(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _ok_origin(self):
        """Doosri website (CSRF) se aaya hukm rokna: Origin/Referer sirf apna, aur gupt token zaroori."""
        port = str(CFG["web_port"]); mine = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
        if CFG.get("web_host") not in ("127.0.0.1", "localhost"): mine.add(f"http://{self.headers.get('Host','')}")
        o = self.headers.get("Origin") or ""
        if o and o not in mine: return False
        r = self.headers.get("Referer") or ""
        if r and not any(r.startswith(m + "/") or r == m for m in mine): return False
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        return self.headers.get("X-Visual-Token") == WEB_TOKEN or q.get("t", [""])[0] == WEB_TOKEN

    def _ok_pin(self):
        pin = CFG.get("web_pin")
        if not pin: return True
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        return self.headers.get("X-Pin") == pin or q.get("pin", [""])[0] == pin

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        try:
            self.end_headers(); self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass   # browser ne beech mein page band/refresh kiya: koi baat nahi

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            with open(os.path.join(HERE, "web", "index.html"), encoding="utf-8") as f:
                page = (f.read().replace("{{NAME}}", CFG["assistant_name"]).replace("{{OWNER}}", CFG["owner_name"])
                        .replace("{{TOKEN}}", WEB_TOKEN))
            return self._send(200, page, "text/html; charset=utf-8")
        if not self._ok_pin(): return self._send(401, '{"error":"pin"}')
        if path.startswith("/api/") and path not in OPEN_GET and not self._ok_origin():
            return self._send(403, '{"error":"ye hukm VISUAL ke apne page se nahi aaya"}')
        if path == "/api/status":
            return self._send(200, json.dumps({"name": CFG["assistant_name"], "brain": providers_available(),
                "termux_api": has("termux-battery-status"), "screen": bool(CFG.get("adb_target")),
                "creations": sorted(os.listdir(CREATIONS)), "facts": len(MEMORY["facts"]),
                "version": VERSION, "last_brain": LAST_BRAIN,
                "mood": mood_label(), "voice": mood_voice()}, ensure_ascii=False))
        if path.startswith("/creations/"):
            p = _safe(urllib.parse.unquote(path[len("/creations/"):]))
            if not os.path.exists(p): return self._send(404, "nahi mila", "text/plain")
            ext = p.rsplit(".", 1)[-1].lower()
            ct = {"html": "text/html", "htm": "text/html", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                  "svg": "image/svg+xml", "js": "text/javascript", "css": "text/css"}.get(ext, "text/plain")
            with open(p, "rb") as f: return self._send(200, f.read(), ct + "; charset=utf-8")
        if path == "/live.js":
            with open(os.path.join(HERE, "web", "live.js"), encoding="utf-8") as f:
                return self._send(200, f.read(), "text/javascript; charset=utf-8")
        if path == "/api/tasks":
            items = sorted(TASKS.values(), key=lambda x: x["started"])[-8:]
            return self._send(200, json.dumps([{k: t[k] for k in ("id", "goal", "status", "report", "announced")} | {"steps": t["steps"][-5:]} for t in items], ensure_ascii=False))
        if path.startswith("/api/tasks/announced/"):
            tid = path.rsplit("/", 1)[-1]
            if tid in TASKS: TASKS[tid]["announced"] = True
            return self._send(200, "{}")
        if path == "/api/live/config":
            return self._send(200, json.dumps(live_config(), ensure_ascii=False))
        if path == "/api/tts":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            data = neural_tts(q.get("text", [""])[0], q.get("v", [None])[0])
            if data: return self._send(200, data, "audio/mpeg")
            return self._send(404, "no neural tts", "text/plain")
        if path.startswith("/p/"):
            parts = urllib.parse.unquote(path[3:]).split("/", 1)
            try:
                root = _proj(parts[0]); rel = parts[1] if len(parts) > 1 and parts[1] else "index.html"
                f = _inside(root, rel)
                if os.path.isdir(f): f = os.path.join(f, "index.html")
                ext = f.rsplit(".", 1)[-1].lower()
                ct = {"html": "text/html; charset=utf-8", "js": "text/javascript", "css": "text/css", "png": "image/png", "jpg": "image/jpeg",
                      "jpeg": "image/jpeg", "svg": "image/svg+xml", "mp3": "audio/mpeg", "ogg": "audio/ogg", "wav": "audio/wav",
                      "json": "application/json", "webp": "image/webp", "mp4": "video/mp4"}.get(ext, "text/plain; charset=utf-8")
                with open(f, "rb") as fh: return self._send(200, fh.read(), ct)
            except Exception as e:
                return self._send(404, f"nahi mila: {e}", "text/plain; charset=utf-8")
        if path == "/shots/screen":
            p = os.path.join(SHOTS, "screen_small.jpg")
            if os.path.exists(p):
                with open(p, "rb") as f: return self._send(200, f.read(), "image/jpeg")
        self._send(404, "nahi mila", "text/plain")

    def do_POST(self):
        if not self._ok_pin(): return self._send(401, '{"error":"pin"}')
        if not self._ok_origin(): return self._send(403, '{"error":"ye hukm VISUAL ke apne page se nahi aaya"}')
        if "application/json" not in (self.headers.get("Content-Type") or ""): return self._send(415, '{"error":"json chahiye"}')
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n > 12_000_000: return self._send(413, '{"error":"bahut bada"}')
        try: data = json.loads(self.rfile.read(n) or b"{}")
        except Exception: return self._send(400, '{"error":"json"}')
        if urllib.parse.urlparse(self.path).path == "/api/heard":
            who = data.get("who", "user"); text = (data.get("text") or "").strip()
            convo_add(who, text); note = ""
            if who == "user" and text:
                heart, crisis = heart_context(text)
                if crisis:
                    note = ("[DIL] Owner ki baat mein khud ko nuksaan pahunchane ka ishaara hai. Abhi sab kaam chhodo, pyaar aur dhyaan se suno, "
                            "judge mat karo, akela mat chhodo. Saaf kaho ki kisi apne ko abhi bulaye ya call kare, aur Tele-MANAS ka free 24x7 "
                            "number 14416 (ya 1-800-891-4416) do; khatra turant ho to 112.")
            return self._send(200, json.dumps({"mood": mood_label(), "note": note}, ensure_ascii=False))
        if urllib.parse.urlparse(self.path).path == "/api/tool":
            name = data.get("name", ""); args = data.get("args") or {}
            PENDING_IMAGES.clear()
            res = run_tool(name, args) if name in TOOLS else f"tool '{name}' nahi hai"
            if res.startswith(("ERROR", "ROKA")): mood_update(-0.05, 0.05)
            imgs = [u for _, u in PENDING_IMAGES]; PENDING_IMAGES.clear()
            return self._send(200, json.dumps({"result": res[:7000], "images": imgs, "mood": mood_label(),
                                              "restart": name == "self_restart" and RESTART_PENDING["v"]}, ensure_ascii=False))
        if urllib.parse.urlparse(self.path).path == "/api/chat":
            steps = []
            reply = chat("web", data.get("text", ""), data.get("image"), events=lambda k, t: steps.append(t), voice=bool(data.get("voice")))
            if data.get("speak_on_phone"): speak(reply)
            return self._send(200, json.dumps({"reply": reply, "steps": steps, "mood": mood_label(), "voice": mood_voice()}, ensure_ascii=False))
        self._send(404, '{"error":"nahi"}')

def run_web():
    host, port = CFG["web_host"], int(CFG["web_port"])
    if host not in ("127.0.0.1", "localhost") and not CFG.get("web_pin"):
        print("Suraksha: web_host bahar khula hai par web_pin khaali hai; 127.0.0.1 par chala raha hoon."); host = "127.0.0.1"
    srv = ThreadingHTTPServer((host, port), Web)
    print(f"\n  {CFG['assistant_name']} taiyaar!  Chrome mein kholo:  http://127.0.0.1:{port}\n")
    if has("termux-open-url") and "--no-open" not in sys.argv:
        threading.Timer(1.5, lambda: sh(["termux-open-url", f"http://127.0.0.1:{port}"])).start()
    srv.serve_forever()

# ---------------------------------------------------------------- telegram (kahin se bhi baat)
def run_telegram():
    tok = CFG.get("telegram_token")
    if not tok: return
    api = f"https://api.telegram.org/bot{tok}/"
    owners = {str(x) for x in CFG.get("telegram_owner_ids", [])}
    offset = 0
    print("  Telegram bot chalu.")
    while True:
        try:
            r = json.loads(http(api + f"getUpdates?timeout=50&offset={offset}", timeout=70))
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message") or {}
                cid = str(m.get("chat", {}).get("id", "")); text = m.get("text") or m.get("caption") or ""
                if not cid: continue
                if text.strip() == "/id":
                    http(api + "sendMessage", {"chat_id": cid, "text": f"Aapka chat id: {cid}"}); continue
                is_owner = cid in owners
                if not is_owner and not CFG.get("telegram_guest_chat"): continue
                img = None
                if m.get("photo") and is_owner:
                    fid = m["photo"][-1]["file_id"]
                    fp = json.loads(http(api + "getFile?file_id=" + fid))["result"]["file_path"]
                    raw = urllib.request.urlopen(f"https://api.telegram.org/file/bot{tok}/{fp}", timeout=60).read()
                    img = "data:image/jpeg;base64," + base64.b64encode(raw).decode()
                reply = chat("tg_" + cid, text, img, allow_tools=is_owner)
                http(api + "sendMessage", {"chat_id": cid, "text": reply[:4000]})
        except Exception as e:
            print("telegram:", e); time.sleep(8)

# ---------------------------------------------------------------- hamesha chalu (screen band par bhi)
STOP_FILE = os.path.join(HOME, "STOP")
HALLUCINATIONS = {"", "thank you.", "thanks for watching!", "you", "bye.", ".", "subtitles by the amara.org community"}

def groq_transcribe(path):
    key = CFG["keys"].get("groq")
    if not key: return ""
    bnd = "----visual" + str(int(time.time() * 1000))
    with open(path, "rb") as f: audio = f.read()
    parts = []
    for k, v in (("model", "whisper-large-v3-turbo"), ("language", "hi"), ("response_format", "json")):
        parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="file"; filename="a.m4a"\r\nContent-Type: audio/mp4\r\n\r\n'.encode()
                 + audio + f"\r\n--{bnd}--\r\n".encode())
    req = urllib.request.Request("https://api.groq.com/openai/v1/audio/transcriptions", data=b"".join(parts),
        headers={"Authorization": "Bearer " + key, "Content-Type": "multipart/form-data; boundary=" + bnd})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read()).get("text", "").strip()
    except Exception as e:
        print("whisper:", e); return ""

def listen_once():
    """Ek baar suno, text lautao (khaali = kuch nahi suna)."""
    if CFG.get("listen_engine") == "groq" and CFG["keys"].get("groq"):
        p = os.path.join(SHOTS, "mic.m4a")
        if os.path.exists(p): os.remove(p)
        sh(["termux-microphone-record", "-f", p, "-l", "7", "-e", "aac"], 10)
        time.sleep(7.3); sh(["termux-microphone-record", "-q"], 5)
        if not os.path.exists(p) or os.path.getsize(p) < 3000: return ""
        t = groq_transcribe(p)
        return "" if t.lower().strip() in HALLUCINATIONS else t
    out = sh(["termux-speech-to-text"], 60).strip()
    return "" if out.startswith("ERROR") else out

def _norm(s): return re.sub(r"[^\w\s]", " ", s.lower())

def run_always():
    """VISUAL hamesha chalu: screen band ho tab bhi sunta hai, tab tak jab tak aap band na bolo."""
    if not has("termux-speech-to-text"):
        print("termux-api chahiye: pkg install termux-api (aur Termux:API app)"); return
    if os.path.exists(STOP_FILE): os.remove(STOP_FILE)
    sh(["termux-wake-lock"], 10)                       # CPU sota nahi, screen band par bhi chalta hai
    name = CFG["assistant_name"]
    sh(["termux-notification", "--id", "visual", "--ongoing", "--priority", "high",
        "--title", f"{name} sun raha hai", "--content", f"'{name} band ho jao' bolo ya Band dabao",
        "--button1", "Band", "--button1-action", f"touch {STOP_FILE}"], 10)
    threading.Thread(target=reminder_loop, daemon=True).start()
    threading.Thread(target=run_telegram, daemon=True).start()
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=data_sync_loop, daemon=True).start()
    speak(f"{name} hamesha chalu hai, {CFG['owner_name']}. Screen band kar do, main sunta rahunga.", wait=True)
    wakes = [_norm(w).strip() for w in CFG.get("wake_words", [])] + [_norm(name).strip()]
    stops = [_norm(s).strip() for s in CFG.get("stop_phrases", [])]
    awake_until = 0; fails = 0
    try:
        while not os.path.exists(STOP_FILE):
            heard = listen_once()
            if os.path.exists(STOP_FILE): break
            if not heard:
                fails += 1; time.sleep(0.3 if fails < 20 else 2); continue
            fails = 0; t = _norm(heard)
            called = any(w and w in t for w in wakes)
            if any(s in t for s in stops) and (called or time.time() < awake_until):
                break
            if CFG.get("wake_word_required") and not called and time.time() > awake_until:
                continue                                # naam nahi liya: ye baat VISUAL ke liye nahi thi
            for w in wakes:                             # naam hata kar asli kaam
                t = re.sub(r"\b" + re.escape(w) + r"\b", " ", t)
            cmd = heard if len(t.strip()) > 1 else ""
            print("Aap:", heard)
            if not cmd:
                speak("Haan boss?", wait=True); awake_until = time.time() + CFG.get("followup_seconds", 40); continue
            rep = chat("voice", cmd, events=lambda k, x: print("  ->", x), voice=True)
            print(name + ":", rep)
            speak(rep, wait=True)
            awake_until = time.time() + CFG.get("followup_seconds", 40)
    except KeyboardInterrupt:
        pass
    speak("Theek hai, main band ho raha hoon. Phir milte hain.", wait=True)
    sh(["termux-notification-remove", "visual"], 10); sh(["termux-wake-unlock"], 10)
    if os.path.exists(STOP_FILE): os.remove(STOP_FILE)
    print(name, "band."); os._exit(0)

# ---------------------------------------------------------------- terminal modes
def run_voice():
    if not has("termux-speech-to-text"):
        print("termux-api chahiye: pkg install termux-api (aur Termux:API app)"); return
    print(f"{CFG['assistant_name']} sun raha hai... ('band karo' bolo rukne ke liye)")
    speak(f"{CFG['assistant_name']} online, {CFG['owner_name']}.")
    while True:
        heard = sh(["termux-speech-to-text"], 60).strip()
        if not heard or heard.startswith("ERROR"): continue
        print("Aap:", heard)
        if re.search(r"band karo|stop|bye|alvida", heard, re.I):
            speak("Theek hai, phir milte hain."); break
        rep = chat("voice", heard, events=lambda k, t: print("  ->", t)); print(CFG["assistant_name"] + ":", rep)
        speak(rep); time.sleep(min(12, 1 + len(rep) / 14))

def run_chat():
    print(f"{CFG['assistant_name']} se likh kar baat karo (exit = band)")
    while True:
        try: t = input("Aap: ").strip()
        except (EOFError, KeyboardInterrupt): break
        if t.lower() in ("exit", "quit"): break
        if t: print(CFG["assistant_name"] + ":", chat("cli", t, events=lambda k, x: print("  ->", x)))

def run_setup():
    print("VISUAL setup. Khaali chhodo to purana rahega.\n")
    def ask(q, cur): v = input(f"{q} [{cur}]: ").strip(); return v or cur
    CFG["assistant_name"] = ask("Assistant ka naam", CFG["assistant_name"])
    CFG["owner_name"] = ask("Aapka naam", CFG["owner_name"])
    print("\nFree dimaag (kam se kam ek key; zyada keys = Sach Engine zyada pakka):\n  Gemini: aistudio.google.com/apikey\n  Groq: console.groq.com/keys\n  OpenRouter: openrouter.ai/keys\n  Mistral: console.mistral.ai\n  Cerebras: cloud.cerebras.ai")
    for p in PROVIDERS:
        cur = CFG["keys"].get(p, ""); show = (cur[:4] + "...") if cur else ""
        v = input(f"{p} key [{show}]: ").strip()
        if v: CFG["keys"][p] = v
    t = input("\nTelegram bot token (BotFather se, chhodna ho to Enter): ").strip()
    if t: CFG["telegram_token"] = t
    ids = input("Aapka Telegram chat id (bot ko /id bhejo; comma se kai): ").strip()
    if ids: CFG["telegram_owner_ids"] = [i.strip() for i in ids.split(",") if i.strip()]
    save_json(CONF, CFG); os.chmod(CONF, 0o600); print("\nSave ho gaya:", CONF)

def run_adb_setup():
    if not has("adb"): print("Pehle: pkg install android-tools"); return
    print("""Screen dekhne/chalane ke liye (ek baar):
1. Settings > About phone > Build number 7 baar dabao (Developer options).
2. Settings > Developer options > Wireless debugging ON (Wi-Fi juda ho).
3. 'Pair device with pairing code' dabao. Termux ko split-screen ya floating mein rakho.""")
    pp = input("Pairing wala IP:port (jaise 192.168.1.5:41234 ya sirf port): ").strip()
    code = input("Pairing code (6 ank): ").strip()
    if ":" not in pp: pp = "localhost:" + pp
    print(sh(["adb", "pair", pp, code], 30))
    cp = input("Ab Wireless debugging screen par dikhne wala IP:port (connect wala, sirf port bhi chalega): ").strip()
    if ":" not in cp: cp = "localhost:" + cp
    print(sh(["adb", "connect", cp], 20))
    CFG["adb_target"] = cp; save_json(CONF, CFG)
    print(adb("shell", "echo", "VISUAL screen se juda!"))

def main():
    default = "always" if has("termux-speech-to-text") else "web"
    mode = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else default
    if mode == "app": mode = "web"
    if mode == "setup": return run_setup()
    if mode == "adb": return run_adb_setup()
    if mode == "restore": return print(data_restore())
    if mode == "sync": return print(data_sync())
    if not providers_available(): print("Note: koi API key nahi. Pehle chalao: python visual.py setup")
    if mode == "always":
        if "--no-open" not in sys.argv: sys.argv.append("--no-open")
        return run_always()
    if mode == "stop":
        open(STOP_FILE, "w").close(); return print("Band karne ka sandesh bhej diya.")
    threading.Thread(target=reminder_loop, daemon=True).start()
    if mode == "voice": return run_voice()
    if mode == "chat": return run_chat()
    threading.Thread(target=run_telegram, daemon=True).start()
    if not os.environ.get("VISUAL_SELFTEST"): threading.Thread(target=data_sync_loop, daemon=True).start()
    run_web()

CORE_TOOLS = set(TOOLS)
load_plugins()
if PLUGIN_ERRORS: print("Plugin galtiyan:", PLUGIN_ERRORS)

if __name__ == "__main__":
    main()
