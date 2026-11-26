"""On-device VISUAL learning loop for Android/Termux.

Collects bounded public research metadata into the phone's persistent KB,
exports only rights-eligible records to training staging, and writes an
auditable cycle report. It deliberately does NOT pretend that corpus export
is neural-network training: a model-specific trainer must be configured and
validated separately before weights can change.
"""
import argparse
import json
import os
import shutil
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TOPICS = [
    "deep_learning", "computer_vision", "multimodal_ai",
    "computer_science_methods", "engineering", "semiconductor_research",
    "electronics_circuits", "robotics_agents", "robotics_perception_control",
    "language_culture", "speech_voice", "audio_environment",
    "memory_cognition", "learning_intelligence", "open_hardware",
]

STOP = False


def _stop(_signum, _frame):
    global STOP
    STOP = True


def _atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _free_bytes(path):
    return shutil.disk_usage(str(path)).free


def run_cycle(home, topics, max_requests, per_request, min_free_gb):
    # Import lazily so --help works even before project dependencies are installed.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins" / "knowledge_base"))
    from global_research import collect_global_research
    from knowledge_engine import knowledge_stats
    from training_prep import prepare_training_corpus

    home = Path(home).expanduser().resolve()
    home.mkdir(parents=True, exist_ok=True)
    minimum = int(min_free_gb * (1024 ** 3))
    free_before = _free_bytes(home)
    if free_before < minimum:
        raise RuntimeError(
            f"Phone storage safety stop: {free_before} bytes free; "
            f"configured minimum is {minimum} bytes."
        )

    before = knowledge_stats(home)
    collection = collect_global_research(
        topics=topics, per_request=per_request,
        max_requests=max_requests, home=home,
    )
    after = knowledge_stats(home)

    # Export is a staging operation only. It never modifies model weights.
    staging = home / "training_staging"
    corpus = prepare_training_corpus(home=home, output_dir=staging)
    free_after = _free_bytes(home)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": "Android/Termux local storage",
        "topics": topics,
        "collection": {
            "requests_attempted": collection.get("requests_attempted", 0),
            "successful_requests": collection.get("successful_requests", 0),
            "empty_results": collection.get("empty_results", 0),
            "failed_requests": collection.get("failed_requests", 0),
            "indexed_characters": collection.get("indexed_characters", 0),
            "task_offset": collection.get("task_offset"),
            "next_task_offset": collection.get("next_task_offset"),
        },
        "knowledge_base_before": before,
        "knowledge_base_after": after,
        "delta": {
            "sources": after["sources"] - before["sources"],
            "documents": after["documents"] - before["documents"],
            "chunks": after["chunks"] - before["chunks"],
        },
        "training_corpus": corpus,
        "storage": {
            "free_bytes_before": free_before,
            "free_bytes_after": free_after,
            "minimum_free_bytes": minimum,
        },
        "model_training": {
            "started": False,
            "reason": (
                "This project currently has no configured on-device base model, "
                "tokenizer, model-specific SFT/LoRA trainer, or held-out evaluation. "
                "The JSONL files are staging data, not trained weights."
            ),
        },
    }
    _atomic_json(home / "phone_learning_last_report.json", report)
    with (home / "phone_learning_history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description="VISUAL continuous on-phone data collection and training-corpus preparation")
    parser.add_argument("--home", default=str(Path.home() / ".visual"))
    parser.add_argument("--loop", action="store_true", help="repeat cycles until stopped")
    parser.add_argument("--interval-hours", type=float, default=6.0)
    parser.add_argument("--max-requests", type=int, default=30, help="bounded provider-query tasks per cycle (max 300)")
    parser.add_argument("--per-request", type=int, default=10, help="records requested per provider query (max 25)")
    parser.add_argument("--min-free-gb", type=float, default=1.0, help="stop before consuming phone's last free storage")
    parser.add_argument("--topics", default=",".join(DEFAULT_TOPICS))
    args = parser.parse_args()

    if not (0 < args.interval_hours <= 168):
        parser.error("--interval-hours must be >0 and <=168")
    if not (1 <= args.max_requests <= 300):
        parser.error("--max-requests must be 1..300")
    if not (1 <= args.per_request <= 25):
        parser.error("--per-request must be 1..25")
    if not (0.1 <= args.min_free_gb <= 1000):
        parser.error("--min-free-gb must be 0.1..1000")

    topics = [x.strip() for x in args.topics.split(",") if x.strip()]
    if not topics:
        parser.error("At least one topic is required")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    home = Path(args.home).expanduser()
    home.mkdir(parents=True, exist_ok=True)
    lock = home / "phone_learning.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SystemExit(f"Learning loop already appears active: {lock}")
    os.write(fd, str(os.getpid()).encode("ascii"))
    os.close(fd)

    try:
        while not STOP:
            report = run_cycle(home, topics, args.max_requests, args.per_request, args.min_free_gb)
            print(json.dumps({
                "requests": report["collection"]["requests_attempted"],
                "new_documents": report["delta"]["documents"],
                "train_rows": report["training_corpus"]["counts"],
                "model_training_started": report["model_training"]["started"],
                "free_bytes": report["storage"]["free_bytes_after"],
                "report": str(home / "phone_learning_last_report.json"),
            }, ensure_ascii=False), flush=True)
            if not args.loop or STOP:
                break
            deadline = time.monotonic() + args.interval_hours * 3600
            while not STOP and time.monotonic() < deadline:
                time.sleep(min(30, max(1, deadline - time.monotonic())))
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
