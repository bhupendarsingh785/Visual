# VISUAL Remote Browser Bridge

## Purpose

Expose the existing VISUAL browser chat panel from the Android phone through a temporary HTTPS link. The agent, tools, memory, and knowledge database continue running on the phone; the tunnel only forwards browser traffic to the local VISUAL web server.

## Start

1. Update VISUAL to the branch/commit containing this feature.
2. In Termux run `visual remote`.
3. Enter the email address that should be allowed to open the panel.
4. Wait for Cloudflare to print a `https://....trycloudflare.com` URL.
5. Open that URL in a browser. Cloudflare sends a one-time PIN to the allowed email address.
6. Keep Termux, VISUAL, the tunnel process, phone power and internet active while using the link.

Stop with Ctrl+C. The temporary URL expires when the tunnel process stops; a new run creates a different URL.

## Security

- The local VISUAL server remains bound to loopback; no router port is opened.
- Cloudflare Quick Tunnel email OTP gates access before requests reach the phone.
- VISUAL's browser API still requires its per-session secret token and same-origin Origin/Referer checks. Same-origin HTTPS host validation supports the reverse-tunnel hostname without accepting arbitrary cross-site origins.
- Never remove the token check, disable the email gate, or expose port 8765 directly.
- Do not share the generated URL. If it is shared accidentally, stop the tunnel immediately.
- The web panel can execute tools available to the VISUAL owner. Keep VISUAL's risky-action confirmation enabled and allow only your own email.
- Cloudflare Quick Tunnels are temporary development links, not a permanent production URL or uptime-guaranteed service.

## Limits

This is not a hosted copy of VISUAL. If the phone is offline, Termux is stopped, Android kills the process, or the tunnel exits, the link stops working. The URL is generated only after the phone starts the tunnel; a static URL cannot be pre-created from GitHub.
