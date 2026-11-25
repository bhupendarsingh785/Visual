#!/data/data/com.termux/files/usr/bin/bash
# VISUAL update: sabse nayi VISUAL_v*.zip dhoondho, daalo, GitHub par bhejo, chalao (crash ho to khud dobara)
pkill -f "visual.py" 2>/dev/null
f=$(find /storage/emulated/0/ -iname 'VISUAL_v*.zip' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
if [ -n "$f" ]; then echo "Mili: $f"; cd ~ && unzip -o -q "$f"; else echo "(nayi zip nahi mili, jo hai wahi chala raha hoon)"; fi
cd ~/visual || exit 1
python -c "import edge_tts" 2>/dev/null || AIOHTTP_NO_EXTENSIONS=1 pip install -q edge-tts 2>/dev/null || true
# 'visual' command: crash ho to 3 second mein khud dobara chalu
cat > "$PREFIX/bin/visual" <<'EOW'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/visual
case "$1" in setup|adb|stop|chat|keys|brains|sync|restore) exec python visual.py "$@";; esac
while true; do
  python visual.py "$@"; code=$?
  if [ $code -eq 0 ] || [ $code -eq 130 ]; then break; fi
  echo "VISUAL ruk gaya (code $code). 3 second mein khud dobara chalu..."; sleep 3
done
EOW
chmod +x "$PREFIX/bin/visual"
git add . 2>/dev/null && git -c user.name=bhupendarsingh785 -c user.email=bhupendarsingh785@users.noreply.github.com commit -qm "update" 2>/dev/null && git push -q 2>/dev/null || true
echo "Update ho gaya. Chalu kar raha hoon..."; exec visual app
