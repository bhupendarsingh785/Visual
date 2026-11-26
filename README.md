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

## v4.5: phone jaisi jaanch (Python 3.14)
- Saare test phone wale Python 3.14 par bhi chalaye (pehle sirf 3.13 par): sab pass, 79 tools 0 crash.
- CTRL+C dabane par ab lamba laal error nahi aata, bas "⏹ Band kiya (CTRL+C). Ye galti nahi hai."
- `visual keys` mein har key turant save hoti hai; beech mein band kiya to bhi daali hui key nahi khoti.

## v4.4: `visual brains` atakta tha
- Phone par `visual brains` bina kuch dikhaye der tak chalta tha (har AI ki jaanch mein limit par 45 second tak rukna + ek-ek karke intezaar). Ab: turant "⏳ jaanch raha hoon" dikhata hai, sab AI ek saath, kul ~30 second se zyada nahi. Atka hua AI baaki ko nahi rokta.
- Limit bhari ho to ❌ nahi, ⏳ "key sahi hai, thodi der mein chalega".

## v4.3: asli phone ki jaanch se mili galti
- Google ne `gemini-2.5-flash` band kar diya (404 "no longer available"). Ab Gemini ka model naam pakka likha nahi: har din Google ki list se chalu model khud chunta hai (baat ke liye tez, kaam ke liye bada). Model band mile to 1 din ke liye chhod kar turant doosra; config mein purana naam ho to khud hata deta hai.
- Live awaaz ke models bhi Google ki list se (jo is key par sach mein chalte hain).
- Google ki nayi `AQ.` wali keys bhi secret-scanner pakadta hai (GitHub par nahi jaayengi).

## v4.2: Dimaag-chunav (smart router): har kaam ke liye sahi AI
- Ab "ek khatam to doosra" nahi. Har sawaal ki kism pehchaanta hai: baat, Hindi, code, soch/plan, tathya, tasveer, phone-kaam, tez. Har kism mein har AI ka alag number hai.
- Shuru mein number andaze se (jaise code mein DeepSeek/Qwen, Hindi mein Sarvam/Gemini, tez mein Groq/Cerebras). Phir **asli nateejon se khud seekhta hai**: chala ya fail, kitna tez, aur jawab kitna sahi nikla (Sangam ke test, Sach Engine/Parishad ke nyaayadhish, doosre AI ki jaanch). Number `~/.visual/brain_stats.json` mein (GitHub data repo mein bhi).
- **Bhaar baant-ta hai:** har AI ki free minute-limit jaanta hai; ek par zyada bojh ho to limit bharne se pehle doosre ko deta hai.
- **Naye AI aazmata hai:** ~12% baar doosre number par kam aazmaaya AI lagata hai, taaki pata chale kaun behtar hai.
- **Galti maaf bhi karta hai:** ek-do baar fail hone wala AI thodi der peeche jaata hai, 30-60 min mein wapas.
- **Tathya wale jawab ki doosri raay:** kisi doosri company ka AI jawab jaanchta hai; shak ho to Sach Engine (kai AI + internet) se sahi karke deta hai, aur jhootha AI ka number girta hai. Band karna ho: config mein `auto_verify: false`.
- Har AI mein kai keys (comma se) aur duniya ki koi bhi OpenAI-jaisi API jod sakte ho (`visual keys`, ya bolo "ye API jodo"), saath mein batao wo kis kaam mein achhi hai.
- `visual brains`: kaun juda hai + har kaam mein kaun aage.
- Honest note: Live awaaz mode Google Gemini Live par hi chalta hai (doosri company ka Live audio API free mein nahi); par Live se bulaye gaye kaam (Engineer, Sach, Parishad) ye router use karte hain. Sach Engine ab internet khoj fail ho to "internet se jaancha" nahi bolta.

## v4.1: poori jaanch ke baad majbooti
- **Live lambi baat:** pehle Google ki seema se audio baat ~15 min aur camera ke saath sirf ~2 min mein toot jaati thi, aur har ~10 min connection badalne par pichhli baat bhool jaata tha. Ab context compression + session resumption: baat bina toote aage chalti hai.
- **Live mein Google khoj** seedhe (model na maane to apne aap uske bina chalta hai).
- **web_search:** DuckDuckGo fail ho to ab Google khoj (Gemini key se, source links ke saath), phir Wikipedia. Pehle DDG ka page badalne par "kuch nahi mila" bol kar ruk jaata tha.
- **Engineer ke kaam ab gum nahi hote:** restart/crash/phone band hone par kaam `tasks.json` mein rehta hai aur wapas chalu hone par wahin se aage badhta hai (har kaam max 2 baar; teesri baar saaf ❌). Ye bhi GitHub data repo mein jaata hai.
- **Screen control khud judta hai:** phone restart ya Wi-Fi badalne par Wireless debugging ka port badalta hai; ab VISUAL mDNS se naya port dhoondh kar khud jud jaata hai (pairing ek hi baar).
- Volume ka galat input ab crash nahi.
- Jaanch: 78 tools nakli phone par chalaye (0 crash), Sangam 20/20, purane features 14/14, Live (jhooth-pakad, resume, Google-khoj fallback) browser mein, task-resume 6/6. Sab mock par.

## v4.0 "Sangam": kai desh ke free dimaag ek saath
- **13 free/sasti AI services:** America (Gemini, GitHub Models, Groq, OpenRouter free, Cerebras, NVIDIA), Europe (Mistral), China (Zhipu GLM, SiliconFlow, ModelScope, Qwen/DashScope, DeepSeek), Bharat (Sarvam). Jitni key, utna pakka. Key jodo: `visual keys` (har key wahi par jaanchi jaati hai). Haal dekho: `visual brains` ya bolo "kaun-kaun se dimaag jude hain".
- GitHub Models ke liye alag key nahi: phone par `gh auth login` hai to apne aap judta hai.
- Har service par sabse taaqatwar model khud chunta hai (code ke liye DeepSeek/Qwen3/Kimi/GLM/gpt-oss jaise), chat ke liye tez wala. Galat key wali service 30 min ke liye chhod deta hai.
- **ensemble_code (SANGAM CODE):** upgrade/naya feature banate waqt: ek model sakht test likhta hai, 4 alag models code likhte hain, har code alag jagah asli chala kar number milte hain, sabse achha chuna jata hai, galti wale ko doosre model se sudhaarwaya jata hai, do achhe milaaye jaate hain (tabhi jab number na gire), phir install + test + doosre model ka critic. Koi bhi code load na ho to install NAHI karta, saaf ❌ batata hai.
- Galat test pakadna: jo test kisi bhi model se paas na ho (aur galti 'assert' wali ho) use "shayad test galat" likh kar skip karta hai, chhupata nahi. Feature hi gayab ho (ERROR) to wo test kabhi nahi hat-ta.
- **council (Parishad):** mushkil sawaal par 6 models, doosri parat mein har model doosron ki galti pakad kar sudhaarta hai, phir nyaayadhish internet saboot ke saath jawab deta hai.
- **Jhootha daava pakadna (text + Live dono):** "delete kar diya / upgrade karunga" jaisa daava kiya par koi tool nahi chala to VISUAL ko turant wapas bhej kar sahi tool chalwaya jata hai.
- Trash restore ki galti theek (v3.7 mein mitayi cheez wapas nahi aati thi).
- **Sach:** ye sab nakli (mock) servers par jaancha gaya. Asli Groq/Zhipu/Sarvam waghaira se is computer se judna block tha, isliye asli models par pehli jaanch aapke phone par hogi (`visual brains`). Free models ki apni seema hai: ek din/minute mein kam request, aur chhote models galat code dete hain; isliye Sangam kai models + asli test se chunta hai, par 100% guarantee koi nahi de sakta.

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

## Remote browser link (temporary HTTPS)
- `visual remote` creates an email-OTP-protected Cloudflare Quick Tunnel to this phone's existing browser chat panel. The AI agent, tools and local data remain on the phone.
- Keep Termux and the tunnel running; Ctrl+C stops the link. Every start creates a new temporary URL. See `docs/REMOTE_BROWSER_BRIDGE.md`.

## Sach (seemaayein)
- Hamesha "Hey VISUAL" sunne wala wake-word abhi nahi: orb dabao ya `visual voice` chalao.
- Screen control ke liye Wi-Fi + wireless debugging chahiye (bina root ke yahi tarika hai).
- Free key ki daily limit hoti hai; zyada use par doosri key (Groq/OpenRouter) apne aap chalti hai.
