# Memory & Repeat Upgrade Spec

## Lakshya
VISUAL screen band hone par bhi owner ki baatein sunta rahe, aur "dohrao" kehne par pichhli kahi baat ko repeat kare.

## Research (best tareeke)
- Screen-off state mein VISUAL chalta rahega (base guarantee). Sirf last statement ko memory mein save karna hai taaki screen on/off cycle mein na khoye.
- "dohrao" trigger ko voice input stream mein detect karna hoga.
- Storage: simple in-memory variable + optional file backup (creations/memory_repeat.json) taaki restart ke baad bhi mile.

## Features
1. store_last(text): pichhli baat save kare (screen off hone par bhi rahe).
2. recall_last(): pichhli baat lautaye.
3. handle_dohrao(): agar input mein "dohrao" ho to pichhli baat bolne ke liye return kare.
4. Agar koi pehli baat nahi hui to: "Abhi tak kuch nahi suna, boss."
5. Screen off/on event par memory clear na ho.

## Architecture
- plugins/memory_repeat/plugin.py : entry point, @tool functions
- plugins/memory_repeat/memory_store.py : storage logic (in-memory + JSON file)
- plugins/memory_repeat/test_memory_repeat.py : unittest

## Galti sambhalna
- File corrupt ho to in-memory se chalao, error log karo.
- Koi baat nahi hai to saaf message do.

## Config/Keys
Koi API key nahi chahiye.

## PAKKE TEST (acceptance criteria)
- store_last("namaste") -> recall_last() == "namaste"
- handle_dohrao("dohrao") -> "namaste" return kare
- handle_dohrao("kuch nahi") -> None (trigger nahi mila)
- Empty state -> "Abhi tak kuch nahi suna, boss."