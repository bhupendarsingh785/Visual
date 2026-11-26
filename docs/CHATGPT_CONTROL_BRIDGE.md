# VISUAL ChatGPT Control Bridge

## Purpose
The Android phone remains the executor. A Termux process polls the existing private repository bhupendarsingh785/visual-data for issues labelled visual-command. ChatGPT can place a bounded request in that private queue through the connected GitHub app; the phone executes it locally and posts the result as an issue comment.

This is not a remote shell. It rejects Python, shell commands, arbitrary URLs, file paths, and arbitrary tool names.

## Security gates
- GitHub CLI account must be bhupendarsingh785.
- Queue repository must report private=true; otherwise startup is refused.
- Issue author must be bhupendarsingh785 and label must be visual-command.
- Only knowledge_collect_global_research and knowledge_status are allowed.
- Research limits: per_request 1–25; max_requests 1–300.
- Each command has a unique nonce and expiry (maximum 24 hours).
- Issue ID is persisted before execution with file mode 0600. Interrupted commands are marked unknown and never automatically replayed.
- State corruption fails closed; it does not reset the idempotency ledger.
- Output is capped and common API-key formats are redacted. Issues are closed after handling.
- Revoke GitHub CLI credentials if the phone is lost.

## Start on phone
1. Update VISUAL to the commit containing this bridge.
2. Ensure gh auth login is complete for bhupendarsingh785.
3. Run: visual control --check
4. Run: visual control
Keep Termux alive; CTRL+C stops polling.

## Issue body format
The issue body must be raw JSON (no Markdown code fence):
{
  "action": "knowledge_collect_global_research",
  "args": {
    "topics": "deep_learning,ai,coding,computer_vision,multimodal_ai,robotics,semiconductor_research,electronics_circuits,materials_science,engineering,android,india,languages,speech_voice",
    "per_request": 25,
    "max_requests": 300
  },
  "nonce": "a-unique-random-identifier-1234",
  "expires_at": 1795700000
}
Expiry is Unix time. Status command uses action knowledge_status and empty args.

## Limits
Only two Knowledge Base actions are enabled in this first version. The bridge does not expose arbitrary phone tools, files, or a general-purpose agent. ChatGPT messages do not execute by themselves: the private issue must be created and the phone poller must be running. GitHub and internet access are required; database writes remain on the phone. The existing visual remote browser tunnel is a separate feature.
