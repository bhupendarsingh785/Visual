#!/data/data/com.termux/files/usr/bin/bash
# VISUAL safe updater: clean git update, backup, offline checks, automatic rollback.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ROOT="$HOME/.visual/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$BACKUP_ROOT/update-$STAMP"
mkdir -p "$BACKUP_ROOT"

if [ ! -d "$ROOT/.git" ]; then
  echo "ROKA: $ROOT mein Git repository nahi mili. Purane ZIP updater se automatic extract nahi hoga."
  echo "Pehle apni existing VISUAL installation ka backup lekar Git clone/update setup karein."
  exit 1
fi

cd "$ROOT"
BRANCH="$(git branch --show-current)"
if [ -z "$BRANCH" ]; then echo "ROKA: current Git branch pata nahi chali."; exit 1; fi

if [ -n "$(git status --porcelain)" ]; then
  echo "ROKA: local files mein unsaved changes hain. Pehle unka backup/commit karein."
  git status --short
  exit 1
fi

BEFORE="$(git rev-parse HEAD)"
mkdir -p "$BACKUP"
tar --exclude='./.git' -czf "$BACKUP/visual-files.tar.gz" -C "$ROOT" .
printf '%s\n' "$BEFORE" > "$BACKUP/previous-commit.txt"

rollback() {
  code=$?
  if [ "$code" -ne 0 ]; then
    echo "Update/check fail hua. Purane Git commit par rollback kar raha hoon..."
    git reset --hard "$BEFORE" || true
    echo "Rollback commit: $BEFORE"
    echo "File backup: $BACKUP/visual-files.tar.gz"
  fi
  exit "$code"
}
trap rollback EXIT

git fetch origin
git pull --ff-only origin "$BRANCH"

python -m compileall -q visual.py plugins
VISUAL_SELFTEST=1 python -c "import sys; sys.argv=['visual.py']; import visual; required={'dev_task_create','dev_orchestration_start','self_intelligence_audit','store_last','recall_last','handle_dohrao'}; missing=required-set(visual.TOOLS); assert not visual.PLUGIN_ERRORS, visual.PLUGIN_ERRORS; assert not missing, 'missing plugin tools: '+str(sorted(missing))"
python -m unittest discover -s plugins/continuous_listening -p 'test_*.py' -v
python -m unittest discover -s plugins/memory_repeat -p 'test_*.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=plugins/self_intelligence python -m unittest discover -s plugins/self_intelligence -p 'test_*.py' -v
PYTHONPATH=plugins/autonomous_development python -m unittest discover -s plugins/autonomous_development -p 'test_*.py' -v

# Launcher ko tabhi refresh karo jab source checks pass ho chuke hon.
cat > "$PREFIX/bin/visual" <<'EOW'
#!/data/data/com.termux/files/usr/bin/bash
ROOT="$HOME/visual"
cd "$ROOT" || exit 1
case "${1:-}" in remote) shift; exec bash "$ROOT/scripts/visual-remote.sh" "$@";; setup|adb|stop|chat|keys|brains|sync|restore) exec python visual.py "$@";; esac
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

trap - EXIT
echo "Update aur offline checks safal. Backup: $BACKUP"
exec visual app
