# VISUAL — Arjun ka apna AI agent (Android)

Dekhta hai (camera + phone ki screen), sunta hai, bolta hai, sochta hai, phone chalata hai, internet se juda hai, aur khud cheezein banakar dekh bhi sakta hai. Laptop ki zarurat nahi.

## Kya-kya kar sakta hai
- **Baat:** Hindi/Hinglish mein bolo, wo bol kar jawab dega (glowing orb app).
- **Dekhna:** camera se dekhta hai ("ye kya hai?"), aur aapki **phone screen** dekh kar khud tap / type / scroll karta hai.
- **Phone:** apps kholna, torch, volume, brightness, alarm, reminder, battery, location, notifications padhna, SMS padhna/bhejna, call, WhatsApp message.
- **Internet:** taaza khabar, mausam, daam khojna, koi bhi page padhna, YouTube/Maps kholna.
- **Banana:** code, HTML game, kahani, notes banata hai, upar ✦ chip mein dikhte hain, khol kar dekh sakta hai, Python chala sakta hai.
- **Yaad:** aapki baatein yaad rakhta hai (`~/.visual/memory.json`).
- **Kahin se bhi:** Telegram bot se door baithe bhi chalao; dost bhi baat kar sakte hain (unke liye phone control band).
- **Suraksha:** SMS, call, WhatsApp, code chalana: pehle poochhta hai, aap "haan" bolo tabhi karta hai. Payment ka aakhri "Pay" khud nahi dabata.

## v3.6: poori jaanch (audit) ke baad
- **Har tool asli mein chala kar jaancha** (75 tools, nakli phone par). AI ke galat inputs ab crash nahi karte:
  text→number/haan-na, faltu keys hatana, zaroori input ki kami saaf batana, alag format ke arguments samajhna.
- **Suraksha:** koi doosri website VISUAL ko chupke hukm (SMS/call) nahi de sakti, na API key padh sakti.
  Sirf VISUAL ka apna page (gupt token + origin jaanch) hukm de sakta hai.
- **Free limit (429):** model ko kuch der chhod kar doosra, sab band hon to intezaar karke dobara; kaam adhoora nahi.

## v3.3: ADVANCED self-upgrade (quality gate ke saath)
Bada upgrade ab is tareeke se hota hai (jaise badi AI labs karti hain), aur **code isse zabardasti karwata hai**:
1. **Research** (best tareeke, asli libraries)  2. **SPEC** (poora design, advanced features, test)
3. **Build**: kai files ka plugin (`plugins/<naam>/plugin.py` + modules + `test_*.py`)  4. **Test**: asli unittest
5. **Critic**: alag sakht reviewer, SCORE 0-10. **8 se kam = sudhaar karo**, phir dobara test + critic.
**Quality Gate:** jab tak SPEC + tests pass + score >= 8 na ho, Engineer "ho gaya" nahi bol sakta. Upgrade ke liye dugne kadam.
Report mein critic score aur test nateeja aata hai.

## Data GitHub mein (v3.2)
- VISUAL ka data (yaadein `memory.json`, baatcheet `convo.jsonl`, banayi cheezein `creations/`, settings bina keys ke)
  aapke **PRIVATE** repo `visual-data` mein har 30 minute apne aap jaata hai. Bolo "data sync karo" to turant.
- **Suraksha:** repo private na ho to data nahi bhejta; API keys/password kabhi nahi jaate (har file jaanch kar key hata deta hai).
- **Naya phone:** VISUAL install karke `gh auth login`, phir `visual restore` → saari yaadein wapas. Keys `visual setup` se dobara.
- Code repo `Visual` public hai to use private karne ke liye: `gh repo edit bhupendarsingh785/Visual --visibility private --accept-visibility-change-consequences`

## v3.1: poori jaanch ke baad mazboot
- **Live mein Dil + yaad:** har baat server par darj (mood, apnapan, yaad); reconnect par pichhli baatcheet yaad rehti hai; `recall` se purani baatein.
- **Live mein sankat-suraksha:** khud ko nuksaan ki baat pakad kar Live ko turant dhyaan + Tele-MANAS 14416 ka nirdesh.
- **Live camera:** camera chalu ho to har second ek tasveer, VISUAL dekh kar baat karta hai.
- **Kisi bhi API se judna:** `call_api` (key `{{NAAM}}` se lagti hai, output mein kabhi nahi dikhti).
- **Crash ho to khud dobara chalu:** `visual` command 3 second mein restart karta hai.
- **Update:** zip download karke `bash ~/visual/update.sh` (sabse nayi zip khud dhoondhta hai).

## v3.0 ENGINEER: do dimaag (asli advanced agent ka tareeka)
- **Live (bolne wala dimaag):** tez baat + chhote kaam (40 chune hue tools, taaki galat tool na chune).
- **Engineer (gehra dimaag):** bada kaam (app/system, coding, debugging, khud ka upgrade, integration, gehri research) peeche chalta hai.
  Aapki key par jo **sabse taaqatwar model** mile wo khud chunta hai (jaise koi "pro" model), aur
  **plan → code → jaanch (verify_code / chala kar) → galti ki asli wajah → theek → dobara jaanch** karta hai, 60 kadam tak.
  Kaam pura hone par Live **bolkar** batata hai; screen par report (KYA HUA / KAISE CHALAYE / JAANCH / LINK / KAMI).
- **Khud ki galti dhoondhna:** har error ki diary (`~/.visual/errors.log`), `self_diagnose` (dimaag, internet, phone, GitHub, awaaz, plugins),
  `self_errors` (trace ke saath). Engineer inhi se apni galti dhoondh kar self_edit/self_plugin se theek karta hai.
- Settings: `smart_model` (khud chunna band karke koi model fix karo), `engineer_steps`, `live_tool_names`.

## Sach Engine (v2.2): jhooth pakdo, sach nikaalo
- **cross_check**: ek sawaal kai free models (Gemini, OpenRouter, Groq, Mistral, Cerebras: jinki key ho) se alag-alag + internet saboot;
  jahan mel na khaaye wahi jhooth. Nateeja: SACH / BHAROSA (ucch-madhyam-kam) / GALAT-SHAK / SOURCES.
- **check_packages**: AI models aksar nakli library ke naam bana dete hain; har package asli PyPI/npm par jaancha jaata hai.
- **check_url**: API link zinda hai ya nahi.
- **verify_code**: syntax, imports ki libraries asli hain ya nahi, tests. "Ho gaya" isi ke baad.
- **Internet hamesha**: DuckDuckGo → DuckDuckGo lite → Wikipedia (English/Hindi).
- Zyada free keys = zyada pakka cross-check (`visual setup` mein Mistral/Cerebras key optional).

## Khud ko upgrade (v2.1)
Bolo: *"khud mein mausam batane ka system jodo"*, *"Spotify se connect ho jao"*, *"apni programming advance karo"*.
VISUAL khud: apna code padhta hai → plugin (`plugins/*.py`) ya main code badalta hai → **backup + test** →
fail ho to **purana wapas** → pass ho to **khud restart** + GitHub push → Live naye kaam ke saath dobara judta hai.
Suraksha ke niyam (khatarnak command rokna, key bachana, SMS/call se pehle poochhna, helpline) koi upgrade nahi hata sakta.
Galat laga to bolo: *"pichhla upgrade wapas lo"* (self_rollback).

## VISUAL LIVE (v2.0): videos jaisa tez, real-time baat
- **Mic ek baar dabao**: awaaz seedhe Google **Gemini Live** tak stream hoti hai, jawab turant awaaz mein (alag-alag text/TTS ke kadam nahi).
- **Beech mein tok sakte ho**: aap bolo to VISUAL turant chup hoke sunta hai.
- **Phone ka echo-cancel**: VISUAL ki apni awaaz mic mein wapas nahi jaati.
- **Saare tools Live se**: phone, apps, GitHub, builder, research; SMS/call jaise kaam se pehle screen par Haan/Nahi.
- Free models (Google pricing ke hisaab se): `gemini-3.1-flash-live-preview`, `gemini-2.5-flash-native-audio-preview-12-2025`; ek na chale to doosra apne aap.
- Live na chale (key/limit) to purana mode apne aap chalu.
- Settings: `live_voice` (Charon, Puck, Kore, Fenrir, Aoede), `live_models`, `live_mode: false` (Live band).

## Dil (v1.5): samajh, ehsaas aur apnapan
Research (empathetic agents: mood pehchaan + pakki personality + yaad + aage ki soch) ke hisaab se:
- **Mood pehchaanta hai:** udaas, khush, gussa, tension, thakaan, utsah (Hindi + Hinglish + emoji), aur usi hisaab se jawab deta hai.
- **Apna mood:** khush / utsahit / shaant / chintit. Baaton se badalta hai; orb ka rang aur awaaz (pitch/speed) usi se badalte hain.
- **Apnapan:** zaroori baatein yaad (exam, interview) aur baad mein "kaisa gaya?"; kaafi din baad aao to khushi se swagat.
- **Sachcha saathi:** chaploosi nahi, galat ho to pyaar se bolega; jaate waqt guilt nahi; kabhi nahi kahega ki wo insaan hai.
- **Sankat mein:** khud ko nuksaan ki baat par sabse pehle dhyaan se sunta hai aur Tele-MANAS 14416 (free, 24x7) batata hai.
- **Soch:** mushkil kaam se pehle `think`, baad mein khud jaanch.
- **Achhi Hindi awaaz:** Microsoft neural (Madhur/Swara, edge-tts, internet chahiye); awaaz wali baat mein jawab Devanagari Hindi mein.
- **Gehri research:** `deep_research` = kai khoj + pages padh kar source ke saath jawab.
- **Live deploy:** `deploy_web` = GitHub Pages link (repo public karna padta hai, pehle poochhta hai).

## Builder agent (v1.4): bolo, aur poora project ban jaaye
Bas bolo: *"VISUAL, ek doctor appointment app banao"* ya *"music player banao, background music ke saath"*.
VISUAL khud:
1. Plan banata hai (features, screens, data), aur khud tay karta hai ki kya chahiye.
2. `~/visual-projects/<naam>` mein alag project banata hai, code likhta hai, zaroori packages (pip/pkg/npm) install karta hai.
3. Free music/image/icon khud dhoondh kar download karta hai (licence credit README mein).
4. Code chala kar test karta hai, error aaye to khud theek karta hai.
5. Aapke GitHub par **alag private repo** banakar push karta hai aur link deta hai (phone par `gh auth login` ek baar).
6. Preview: `http://127.0.0.1:8765/p/<project>/`

Suraksha: system mitane wale command apne aap rukte hain; project folder ke bahar likhna mana; API key code mein mili to GitHub par push nahi hota (key `save_secret` se phone par hi rehti hai).

## Install (10 minute, ek baar)
1. **F-Droid** se do apps: **Termux** aur **Termux:API** (Play Store wala Termux purana hai).
2. Termux kholo, ye chalao:
   ```
   pkg install -y git && git clone <aapka-repo-link> visual && cd visual && bash install.sh
   ```
   (ya zip ko `Download` mein rakh kar: `termux-setup-storage`, `cp ~/storage/downloads/VISUAL.zip . && unzip VISUAL.zip && cd visual && bash install.sh`)
3. Setup poochhega: **free Gemini key** daalo → aistudio.google.com/apikey (Groq/OpenRouter key bhi daal sakte ho, ek fail ho to dusra chalega).
4. **Wo step jo sab bhool jaate hain** — Settings > Apps > **Termux:API** > Permissions: Mic, Camera, SMS, Phone, Contacts, Location sab Allow. Aur Settings > Apps > **Termux** > *Display over other apps* ON (apps kholne ke liye). Notifications padhne ke liye: Settings > Notification access > Termux:API ON.

## Chalao
| Command | Kaam |
|---|---|
| `visual` | **Hamesha chalu**: screen band par bhi sunta hai, kaam karta hai, Telegram + web app saath |
| `visual app` | Sirf orb app Chrome mein (mic dabao, bolo) |
| `visual stop` | Band karo (ya bolo "VISUAL band ho jao", ya notification ka **Band** button) |
| `visual chat` | Likh kar baat |
| `visual adb` | **Screen dekhna/chalana** jodo (neeche) |
| `visual setup` | Naam, key, Telegram badlo |

## Screen dekhna + chalana (sabse powerful, ek baar setup)
1. Settings > About phone > Build number **7 baar** dabao.
2. Developer options > **Wireless debugging** ON (Wi-Fi juda ho).
3. Termux mein `visual adb` chalao, "Pair device with pairing code" ka port + code daalo, phir connect wala port.
4. Ab bolo: *"meri screen dekho aur YouTube par lofi chalao"*.
> Phone restart ya Wi-Fi badalne par port badalta hai: dobara `visual adb`.

## Telegram se jodna (kahin se bhi baat)
1. Telegram mein **@BotFather** > `/newbot` > token copy.
2. `visual setup` mein token daalo, `visual` chalao, bot ko `/id` bhejo, wo id setup mein "owner" daalo.
3. Sirf owner phone chala sakta hai; baaki log sirf baat kar sakte hain (`telegram_guest_chat`).

## Hamesha chalu (screen band hone ke baad bhi)
- `visual` chalao, phir screen band kar do. VISUAL wakelock leta hai aur sunta rehta hai jab tak aap na bolo **"VISUAL band ho jao"**.
- Kaam ke liye pehle naam lo: *"VISUAL, torch on karo"*. Uske baad 40 second tak bina naam ke bhi baat kar sakte ho. TV/doosron ki baat par kuch nahi karega. (Har baat sunni ho to config mein `"wake_word_required": false`.)
- "VISUAL, screen band karo" bhi chalta hai (`visual adb` juda ho to).
- **Zaroori settings** (warna Android ise sula deta hai): Settings > Apps > Termux **aur** Termux:API > Battery > **Unrestricted**. Xiaomi/Redmi/Vivo/Oppo/Realme mein: Autostart ON + recent apps mein Termux par **Lock**.
- **Restart ke baad apne aap chalu:** F-Droid se **Termux:Boot** install karke ek baar kholo. install.sh ne boot script bana di hai.
- Agar screen band par sunna ruk jaaye (kuch phones mein Google ki speech service band ho jaati hai): Groq key daalo aur config mein `"listen_engine": "groq"`. Ye mic record karke Groq Whisper se samajhta hai.

## Settings (`~/.visual/config.json`)
`assistant_name`, `owner_name`, `keys`, `models` (jaise `{"gemini":"gemini-2.5-flash"}`), `provider_order`, `confirm_risky`, `speak_replies`, `web_pin` (agar dusre device se kholna ho, `web_host: "0.0.0.0"` ke saath).
Key kabhi GitHub par mat daalna; wo sirf `~/.visual/` mein rehti hai.

## Sach (seemaayein)
- Hamesha "Hey VISUAL" sunne wala wake-word abhi nahi: orb dabao ya `visual voice` chalao.
- Screen control ke liye Wi-Fi + wireless debugging chahiye (bina root ke yahi tarika hai).
- Free key ki daily limit hoti hai; zyada use par doosri key (Groq/OpenRouter) apne aap chalti hai.
