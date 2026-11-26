# VISUAL Android Always-On Runtime

## What this setup provides
- A Termux supervisor starts VISUAL and restarts it after an unexpected Python process failure, with bounded backoff (3–30 seconds).
- A PID file prevents the normal launcher and Termux:Boot from intentionally starting duplicate supervisor loops.
- VISUAL existing run_always() remains responsible for wake-word handling, speech, notifications, reminders, Telegram and web runtime.
- A clean user stop (exit 0) or Ctrl+C (130) is not automatically restarted.

## Android/Termux setup (one-time)
1. Install Termux and Termux:API from the same trusted source; install Termux:Boot too.
2. In Termux run: pkg update && pkg install -y python termux-api. Grant microphone and notification permissions when Android asks.
3. Android Settings → Apps → Termux and Termux:API → Battery → Unrestricted / Don’t optimize (wording varies). Allow background activity/autostart if available. Do not force-stop either app.
4. Open Termux:Boot once after installing it. The installer creates ~/.termux/boot/start-visual.
5. Start with visual or reboot once. Check: tail -f ~/.visual/visual.log.
6. Stop with visual stop or the persistent notification Stop button. Start again with visual.

## Important Android limitation
The Termux notification is an ongoing notification, not proof that Android has granted VISUAL a native Android microphone foreground service. Android/OEM background microphone rules differ by OS version and vendor. Screen-off listening must be verified on the actual phone after granting permissions; battery saver, force-stop, permission revocation, OS updates, calls, and OEM task killers can interrupt it. The supervisor can recover a crashed Python process, but cannot override Android microphone/privacy policy or restart an app after the user force-stops it.

## Voice and privacy
- Wake-word mode is enabled by default; VISUAL processes commands only after its configured wake word or during the follow-up window.
- Keep microphone access visible through Android microphone privacy indicator and VISUAL ongoing notification.
- Do not set wake_word_required=false unless you explicitly want every captured utterance processed.
- “VISUAL band ho jao” and notification Stop are intended to stop listening. visual stop writes the stop signal.

## Verify on the phone
- [ ] visual starts once and shows the ongoing notification.
- [ ] Wake word works with screen on.
- [ ] Wake word works after screen off for 10 minutes, then 30 minutes.
- [ ] A command gets a spoken response and follow-up window behaves as configured.
- [ ] Spoken stop phrase and notification Stop both stop microphone capture.
- [ ] visual stop stops it; visual starts it again.
- [ ] Reboot starts one instance (Termux:Boot); inspect PID and log.
- [ ] Measure battery drain and heat over at least one hour.

Do not claim 24×7 reliability until the device checklist passes on the target phone.
