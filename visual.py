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
}

DEFAULT_CONF = {
    "assistant_name": APP,
    "owner_name": "Arjun",
    "language": "hi-IN",
    "keys": {"gemini": "", "groq": "", "openrouter": ""},
    "models": {},                 # jaise {"gemini": "gemini-2.5-flash"} badalna ho to
    "provider_order": ["gemini", "openrouter", "groq"],
    "web_host": "127.0.0.1", "web_port": 8765, "web_pin": "",
    "telegram_token": "", "telegram_owner_ids": [], "telegram_guest_chat": True,
    "adb_target": "",            # jaise "localhost:37123" (python visual.py adb)
    "speak_replies": True,
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
    if not CFG.get("speak_replies") or not has("termux-tts-speak"): return
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
@tool("Internet par khojo (taaza khabar, jaankari, daam, mausam)", {"query": S("kya khojna hai")})
def web_search(query):
    try:
        page = http("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query), timeout=25)
    except Exception as e:
        return f"search fail: {e}"
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

@tool("Python code chala kar nateeja lo (hisaab, data, file kaam)", {"code": S("python code")}, risky=True)
def run_python(code):
    p = os.path.join(CREATIONS, "_run.py")
    with open(p, "w", encoding="utf-8") as f: f.write(code)
    return sh([sys.executable, p], 60)[:6000]

@tool("Termux shell command chalao", {"command": S("command")}, risky=True)
def run_shell(command): return sh(command, 90)[:6000]

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
- Taaza jaankari (khabar, daam, mausam, score) ke liye web_search, apni yaad se andaaza nahi.
- Owner koi pakki baat bataye (naam, pasand, dost ka number) to remember se yaad rakho.
- Paise bhejna, password, OTP kabhi kisi ko mat do; payment app mein aakhri 'Pay' khud mat dabao, owner se karwao.
- Galti ho ya tool fail ho to seedha batao aur agla upaay do.

Owner ke baare mein yaad:
{facts}
Abhi ka samay: {get_time()}"""

def providers_available():
    order = CFG.get("provider_order") or list(PROVIDERS)
    return [p for p in order if p in PROVIDERS and CFG["keys"].get(p)]

def llm(messages, use_tools=True):
    errs = []
    for p in providers_available():
        info = PROVIDERS[p]; model = CFG.get("models", {}).get(p) or info["model"]
        msgs = messages
        if not info["vision"]:   # tasveer na samjhe to text bana do
            msgs = [dict(m, content=" ".join(c.get("text", "[tasveer]") for c in m["content"]))
                    if isinstance(m.get("content"), list) else m for m in messages]
        body = {"model": model, "messages": msgs, "temperature": 0.6}
        if use_tools: body["tools"] = [t["schema"] for t in TOOLS.values()]
        try:
            r = json.loads(http(info["base"].rstrip("/") + "/chat/completions", body,
                                {"Authorization": "Bearer " + CFG["keys"][p]}, timeout=90))
            return r["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            errs.append(f"{p}: {e.code} {e.read().decode()[:200]}")
        except Exception as e:
            errs.append(f"{p}: {e}")
    if not errs:
        return {"role": "assistant", "content": "Mera dimaag (API key) set nahi hai. Termux mein chalao: python visual.py setup"}
    return {"role": "assistant", "content": "Dimaag se jud nahi paaya: " + " | ".join(errs)[:400]}

YES = re.compile(r"^\s*(haan|ha|haa|han|yes|y|ok|okay|kar do|karo|theek hai|thik hai|bhej do|chalo|done|hmm+)\b", re.I)
NO = re.compile(r"^\s*(nahi|nahin|na|no|mat|cancel|ruko|rehne do)\b", re.I)

def run_tool(name, args):
    t = TOOLS.get(name)
    if not t: return f"tool '{name}' nahi hai"
    try: return str(t["fn"](**args))
    except TypeError as e: return f"galat input: {e}"
    except Exception as e: return f"ERROR: {e}"

def chat(session, user_text, image_url=None, allow_tools=True, events=None):
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

    content = user_text
    if image_url:
        content = [{"type": "text", "text": user_text or "Ye tasveer dekho"}, {"type": "image_url", "image_url": {"url": image_url}}]
    hist.append({"role": "user", "content": content})
    work = [{"role": "system", "content": system_prompt()}] + [m for m in hist[-24:] if not isinstance(m.get("content"), list) or m is hist[-1]]
    reply = ""
    for _step in range(12):
        msg = llm(work, use_tools=allow_tools)
        calls = msg.get("tool_calls") or []
        if not calls:
            reply = (msg.get("content") or "").strip() or "Hmm, kuch samajh nahi aaya. Dobara bolo?"
            break
        work.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for c in calls:
            name = c["function"]["name"]
            try: args = json.loads(c["function"].get("arguments") or "{}")
            except Exception: args = {}
            if name in RISKY and CFG.get("confirm_risky"):
                s["pending"] = {"name": name, "args": args}
                res = "RUKO: ye kaam owner ki 'haan' ke baad hi hoga. Owner se saaf poochho kya karna hai (kisko, kya), aur kaho 'haan' bolein."
            else:
                ev("tool", name); res = run_tool(name, args)
            work.append({"role": "tool", "tool_call_id": c.get("id", name), "content": res[:7000]})
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
    s["history"] = hist[-40:]
    save_mem()
    return reply

# ---------------------------------------------------------------- web app
class Web(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _ok_pin(self):
        pin = CFG.get("web_pin")
        if not pin: return True
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        return self.headers.get("X-Pin") == pin or q.get("pin", [""])[0] == pin

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            with open(os.path.join(HERE, "web", "index.html"), encoding="utf-8") as f:
                page = f.read().replace("{{NAME}}", CFG["assistant_name"]).replace("{{OWNER}}", CFG["owner_name"])
            return self._send(200, page, "text/html; charset=utf-8")
        if not self._ok_pin(): return self._send(401, '{"error":"pin"}')
        if path == "/api/status":
            return self._send(200, json.dumps({"name": CFG["assistant_name"], "brain": providers_available(),
                "termux_api": has("termux-battery-status"), "screen": bool(CFG.get("adb_target")),
                "creations": sorted(os.listdir(CREATIONS)), "facts": len(MEMORY["facts"])}, ensure_ascii=False))
        if path.startswith("/creations/"):
            p = _safe(urllib.parse.unquote(path[len("/creations/"):]))
            if not os.path.exists(p): return self._send(404, "nahi mila", "text/plain")
            ext = p.rsplit(".", 1)[-1].lower()
            ct = {"html": "text/html", "htm": "text/html", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                  "svg": "image/svg+xml", "js": "text/javascript", "css": "text/css"}.get(ext, "text/plain")
            with open(p, "rb") as f: return self._send(200, f.read(), ct + "; charset=utf-8")
        if path == "/shots/screen":
            p = os.path.join(SHOTS, "screen_small.jpg")
            if os.path.exists(p):
                with open(p, "rb") as f: return self._send(200, f.read(), "image/jpeg")
        self._send(404, "nahi mila", "text/plain")

    def do_POST(self):
        if not self._ok_pin(): return self._send(401, '{"error":"pin"}')
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n > 12_000_000: return self._send(413, '{"error":"bahut bada"}')
        try: data = json.loads(self.rfile.read(n) or b"{}")
        except Exception: return self._send(400, '{"error":"json"}')
        if urllib.parse.urlparse(self.path).path == "/api/chat":
            steps = []
            reply = chat("web", data.get("text", ""), data.get("image"), events=lambda k, t: steps.append(t))
            if data.get("speak_on_phone"): speak(reply)
            return self._send(200, json.dumps({"reply": reply, "steps": steps}, ensure_ascii=False))
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
            rep = chat("voice", cmd, events=lambda k, x: print("  ->", x))
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
    print("\nFree dimaag (kam se kam ek key):\n  Gemini: aistudio.google.com/apikey\n  Groq: console.groq.com/keys\n  OpenRouter: openrouter.ai/keys")
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
    run_web()

if __name__ == "__main__":
    main()
