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
