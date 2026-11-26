#!/data/data/com.termux/files/usr/bin/bash
# VISUAL supervisor for Termux/Termux:Boot. Restarts only after unexpected failure.
set -u
ROOT="${VISUAL_HOME_DIR:-$HOME/visual}"
STATE="$HOME/.visual"
LOG="$STATE/visual.log"
PIDFILE="$STATE/supervisor.pid"
mkdir -p "$STATE"
if [ -f "$PIDFILE" ]; then
  old="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
    echo "VISUAL supervisor pehle se chal raha hai (PID $old)."
    exit 0
  fi
fi
printf "%s\n" "$$" > "$PIDFILE"
cleanup() { current="$(cat "$PIDFILE" 2>/dev/null || true)"; [ "$current" = "$$" ] && rm -f "$PIDFILE"; }
trap cleanup EXIT INT TERM
cd "$ROOT" || { echo "VISUAL folder nahi mila: $ROOT" >> "$LOG"; exit 1; }
delay=3
while :; do
  printf "\n[%s] VISUAL start (supervisor)\n" "$(date -Iseconds)" >> "$LOG"
  python "$ROOT/visual.py" always --no-open >> "$LOG" 2>&1
  code=$?
  printf "[%s] VISUAL exit code=%s\n" "$(date -Iseconds)" "$code" >> "$LOG"
  if [ "$code" -eq 0 ] || [ "$code" -eq 130 ]; then exit 0; fi
  sleep "$delay"
  [ "$delay" -ge 30 ] || delay=$((delay * 2))
done
