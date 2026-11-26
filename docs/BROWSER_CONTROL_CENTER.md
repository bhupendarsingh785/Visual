# VISUAL Browser Control Center

VISUAL already includes a mobile-first browser control panel in `web/index.html` and a real-time voice client in `web/live.js`. The Python server serves both from the same origin and connects the panel to the existing agent runtime.

## Start on Android / Termux

From the VISUAL repository directory:

```sh
python visual.py app
```

Open the local panel in Chrome:

```
http://127.0.0.1:8765
```

The configured port is `web_port` in `~/.visual/config.json`. The `app` command runs the browser panel; the default `python visual.py` mode also starts the always-on runtime and optional Telegram integration.

## What the panel can do

- Text chat through `/api/chat`, using VISUAL's existing tool-enabled chat loop and session memory.
- Live voice conversation through `web/live.js` and the Gemini Live API when Gemini credentials and Live mode are configured. The panel also has browser speech-recognition and TTS fallbacks; browser support varies.
- Camera/image input through the camera button or image picker. Camera and microphone permissions must be granted in the browser.
- Show runtime status, available model providers, phone integration status, recent creations, and active/completed engineer tasks.
- Run supported VISUAL tools through the agent. Risky tools remain subject to the configured confirmation gate.

## Knowledge and self-improvement

The Knowledge Base plugin exposes `knowledge_search`, `knowledge_status`, `knowledge_queue_catalog`, and the explicitly risky `knowledge_collect_now` tool. The agent can use the local indexed material when its tool planner selects it. Collection is not automatic merely because the browser is open: explicitly ask VISUAL to collect or search.

Example request in the panel:

> VISUAL, curated catalog ke public sources ko queue karo aur 10-10 ke batch mein collect/index karo. Har batch ke baad downloaded pages, indexed chunks, errors aur storage status batao.

Self-Intelligence exposes audit and improvement-plan tools. Autonomous Development can prepare and test code changes using its configured execution adapter. Keep approval/confirmation enabled for risky actions; do not grant arbitrary shell or repository write access to an untrusted browser session.

## Network and security boundaries

- Default bind address is `127.0.0.1`: the panel is accessible on the same phone only. This is intentional.
- Do not change the bind address to `0.0.0.0` on an untrusted network. A PIN is required for non-loopback binding, but a PIN alone is not a substitute for HTTPS, firewalling, and a private network.
- For access from another device, use a private VPN/tunnel with authentication and TLS; do not expose the Termux port directly to the public internet.
- Keep API keys in the private `~/.visual/config.json` or environment variables. Never put keys in browser JavaScript, screenshots, public commits, or chat messages.
- Browser voice/camera APIs generally require a secure context. `localhost` / `127.0.0.1` is treated as a secure local origin by modern browsers.
- Android battery optimization, Doze, browser suspension, microphone permission policies, and network loss can interrupt background or continuous voice operation.

## Current capability boundary

The panel is a control surface for the existing VISUAL runtime; it does not itself create unlimited intelligence or download datasets. Model reasoning still depends on configured model providers (or a separately installed local model), and large datasets require real device storage, bandwidth, time, and compatible licenses. Local Knowledge Base search can work without a model API after content has been indexed, but natural-language reasoning and voice generation may still require a configured model/provider.
