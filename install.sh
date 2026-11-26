#!/data/data/com.termux/files/usr/bin/bash
# VISUAL installer (Termux). Chalao:  bash install.sh
set -e
echo "== VISUAL install ho raha hai =="
pkg update -y
pkg install -y python termux-api android-tools
pkg install -y python-pillow || echo "(pillow nahi mila, chalega)"
pkg install -y git gh || true
# achhi Hindi neural awaaz (Microsoft Madhur/Swara). Na lage to phone ki awaaz chalegi.
AIOHTTP_NO_EXTENSIONS=1 YARL_NO_EXTENSIONS=1 MULTIDICT_NO_EXTENSIONS=1 FROZENLIST_NO_EXTENSIONS=1 PROPCACHE_NO_EXTENSIONS=1 pip install edge-tts || echo "(edge-tts nahi laga, phone ki awaaz chalegi)"
termux-setup-storage || true
DIR="$(cd "$(dirname "$0")" && pwd)"
# chhota command: 'visual' likho aur chalu
cat > "$PREFIX/bin/visual" <<'EOW'
#!/data/data/com.termux/files/usr/bin/bash
ROOT="$HOME/visual"
cd "$ROOT" || exit 1
case "${1:-}" in setup|adb|stop|chat|keys|brains|sync|restore) exec python visual.py "$@";; esac
if [ "$#" -eq 0 ] || [ "$1" = "always" ]; then
  exec bash "$ROOT/scripts/visual-supervisor.sh"
fi
while true; do
  python visual.py "$@"
  code=$?
  if [ "$code" -eq 0 ] || [ "$code" -eq 130 ]; then exit "$code"; fi
  echo "VISUAL ruk gaya (code $code). 3 second mein dobara chalu..."
  sleep 3
done
EOW
chmod +x "$PREFIX/bin/visual"
echo ""
echo "Ab API key daalo (free Gemini key: aistudio.google.com/apikey)"
python "$DIR/visual.py" setup
echo ""
echo "Ho gaya! Chalane ke liye likho:  visual   (hamesha chalu, screen band par bhi)"
echo "Orb app: visual app  |  Band: bolo VISUAL band ho jao  |  Screen control: visual adb"

# phone restart par apne aap chalu (Termux:Boot app F-Droid se install karo, ek baar kholo)
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-visual <<'EOB'
#!/data/data/com.termux/files/usr/bin/bash
ROOT="$HOME/visual"
mkdir -p "$HOME/.visual"
exec bash "$ROOT/scripts/visual-supervisor.sh" >> "$HOME/.visual/boot.log" 2>&1
EOB
chmod +x ~/.termux/boot/start-visual
echo "Auto-start taiyaar (Termux:Boot app chahiye)."
