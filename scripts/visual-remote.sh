#!/data/data/com.termux/files/usr/bin/bash
# Temporary, email-gated HTTPS access to the VISUAL browser panel.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="$(python -c 'import json,os; p=os.path.expanduser("~/.visual/config.json"); d=json.load(open(p)) if os.path.isfile(p) else {}; print(int(d.get("web_port",8765)))')"
EMAIL="${1:-}"
if [ -z "$EMAIL" ]; then
  read -r -p "Allowed email (Cloudflare will send a one-time PIN): " EMAIL
fi
if [[ ! "$EMAIL" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$ ]]; then
  echo "ERROR: valid email address chahiye."; exit 2
fi
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared install kar raha hoon (Termux package)..."
  pkg install -y cloudflared
fi
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "ERROR: cloudflared install nahi hua."; exit 1
fi
LOCAL="http://127.0.0.1:$PORT"
WEB_PID=""
if ! python -c "import urllib.request; urllib.request.urlopen('$LOCAL/',timeout=2).read(1)" >/dev/null 2>&1; then
  echo "VISUAL browser server chalu kar raha hoon..."
  mkdir -p "$HOME/.visual"
  nohup python "$ROOT/visual.py" app --no-open >> "$HOME/.visual/remote-web.log" 2>&1 </dev/null &
  WEB_PID=$!
  ready=0
  for _ in $(seq 1 30); do
    if python -c "import urllib.request; urllib.request.urlopen('$LOCAL/',timeout=2).read(1)" >/dev/null 2>&1; then ready=1; break; fi
    sleep 1
  done
  if [ "$ready" -ne 1 ]; then
    echo "ERROR: VISUAL web server $LOCAL par start nahi hua. Log: ~/.visual/remote-web.log"
    kill "$WEB_PID" 2>/dev/null || true
    exit 1
  fi
fi
cleanup() {
  if [ -n "$WEB_PID" ]; then kill "$WEB_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM
echo ""
echo "VISUAL remote link bana raha hai."
echo "Access sirf $EMAIL ke email OTP se milega."
echo "Neeche aane wala https://....trycloudflare.com link browser mein kholo."
echo "Phone aur ye Termux session chalu rehna chahiye. Band karne ke liye CTRL+C."
echo ""
cloudflared tunnel --no-autoupdate --url "$LOCAL" --allowed-mail "$EMAIL"
