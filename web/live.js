// VISUAL Live: Gemini Live API se real-time awaaz baatchit (jaise videos wale assistant).
// Mic ek baar khulta hai; awaaz seedhe Gemini tak; jawab turant awaaz mein; beech mein bol sakte ho (interrupt).
// Tool calls (phone, GitHub, builder...) VISUAL server (/api/tool) par chalte hain.
(function () {
  const L = window.VLive = { on: false };
  let ws = null, cfg = null, micCtx = null, micStream = null, worklet = null, outCtx = null,
      playAt = 0, sources = [], modelIdx = 0, setupDone = false, wantOn = false, reconnects = 0, resumeHandle = null, useGS = true, authIdx = 0, lastErr = '',
      userLine = null, aiLine = null, levelTimer = null;

  const WORKLET = `
  class Mic extends AudioWorkletProcessor {
    constructor(o){super();this.ratio=sampleRate/16000;this.buf=[];this.acc=0;}
    process(inputs){const ch=inputs[0]&&inputs[0][0];if(!ch)return true;
      for(let i=0;i<ch.length;i++){this.acc+=1;if(this.acc>=this.ratio){this.acc-=this.ratio;this.buf.push(ch[i]);}}
      if(this.buf.length>=1600){const n=this.buf.length,o=new Int16Array(n);let peak=0;
        for(let i=0;i<n;i++){let s=Math.max(-1,Math.min(1,this.buf[i]));o[i]=s<0?s*0x8000:s*0x7fff;peak=Math.max(peak,Math.abs(s));}
        this.port.postMessage({pcm:o.buffer,peak},[o.buffer]);this.buf=[];}
      return true;}}
  registerProcessor('vmic',Mic);`;

  function b64(buf) { let s = '', b = new Uint8Array(buf); for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000)); return btoa(s); }
  function unb64(str) { const s = atob(str), b = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return b.buffer; }
  function ui(state, label) { if (window.setState) window.setState(state, label); }
  function say(cls, t) { if (window.add) window.add(cls, t); }

  // ---------- awaaz bajana (24 kHz PCM16) ----------
  function playPCM(buf) {
    if (!outCtx) outCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    const i16 = new Int16Array(buf), f = new Float32Array(i16.length);
    for (let i = 0; i < i16.length; i++) f[i] = i16[i] / 32768;
    const ab = outCtx.createBuffer(1, f.length, 24000); ab.copyToChannel(f, 0);
    const src = outCtx.createBufferSource(); src.buffer = ab; src.connect(outCtx.destination);
    const now = outCtx.currentTime; if (playAt < now + 0.03) playAt = now + 0.03;
    src.start(playAt); playAt += ab.duration; sources.push(src);
    src.onended = () => { sources = sources.filter(x => x !== src); if (!sources.length) ui('listening', 'sun raha hoon... (bolo "band ho jao")'); };
    ui('speaking', 'bol raha hoon');
  }
  function stopPlayback() { sources.forEach(s => { try { s.stop() } catch (e) { } }); sources = []; if (outCtx) playAt = outCtx.currentTime; }

  // ---------- mic ----------
  async function startMic() {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
    micCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }));
    await micCtx.audioWorklet.addModule(url);
    const srcNode = micCtx.createMediaStreamSource(micStream);
    worklet = new AudioWorkletNode(micCtx, 'vmic');
    worklet.port.onmessage = (e) => {
      const orb = document.getElementById('orb'); if (orb) orb.style.transform = 'scale(' + (1 + Math.min(.12, e.data.peak * .4)) + ')';
      if (ws && ws.readyState === 1 && setupDone)
        ws.send(JSON.stringify({ realtimeInput: { audio: { data: b64(e.data.pcm), mimeType: 'audio/pcm;rate=16000' } } }));
    };
    srcNode.connect(worklet);   // worklet ko destination se nahi jodte: apni awaaz speaker par nahi
  }
  function stopMic() {
    try { worklet && worklet.disconnect() } catch (e) { }
    try { micStream && micStream.getTracks().forEach(t => t.stop()) } catch (e) { }
    try { micCtx && micCtx.close() } catch (e) { }
    worklet = micStream = micCtx = null;
  }

  // ---------- connection ----------
  const H = () => ({ 'X-Pin': window.VPIN || '', 'X-Visual-Token': window.VTOKEN || '' });
  function liveLog(msg) {   // galti server ki errors.log mein: baad mein 'tail ~/.visual/errors.log' se dikhe
    try { fetch('/api/livelog', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, H()), body: JSON.stringify({ msg }) }) } catch (e) { }
  }
  async function connect() {
    const model = cfg.models[Math.min(modelIdx, cfg.models.length - 1)];
    const auths = cfg.auth || ['key'];
    setupDone = false;
    let url = cfg.url;
    if (auths[authIdx] === 'token') {        // nayi AQ. key: server se chhota token (key browser tak nahi aati)
      let t = null;
      try { t = await fetch('/api/live/token', { headers: H() }).then(r => r.json()); } catch (e) { }
      if (!t || !t.ok) { lastErr = 'token: ' + (t && t.error || 'nahi mila'); liveLog(lastErr); authIdx++; return connect(); }
      url = t.url;
    }
    if (!wantOn) return;
    ws = new WebSocket(url);
    ws.onopen = () => {
      ws.send(JSON.stringify({ setup: {
        model: 'models/' + model,
        generationConfig: { responseModalities: ['AUDIO'],
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: cfg.voice } } } },
        systemInstruction: { parts: [{ text: cfg.prompt }] },
        tools: useGS ? [{ functionDeclarations: cfg.tools }, { googleSearch: {} }] : [{ functionDeclarations: cfg.tools }],   // Google khoj seedhe Live mein
        inputAudioTranscription: {}, outputAudioTranscription: {},
        // lambi baat: bina iske audio session ~15 min aur camera ke saath sirf ~2 min mein khatam (Google docs)
        contextWindowCompression: { slidingWindow: {} },
        // har ~10 min server connection badalta hai: handle se wahi baat-cheet aage chalti hai (yaad nahi tootti)
        sessionResumption: resumeHandle ? { handle: resumeHandle } : {}
      } }));
    };
    ws.onmessage = async (ev) => {
      let txt = ev.data; if (typeof txt !== 'string') txt = await (txt.text ? txt.text() : new Response(txt).text());
      let m; try { m = JSON.parse(txt) } catch (e) { return }
      if (m.setupComplete) { setupDone = true; reconnects = 0; ui('listening', 'LIVE: bas bolo... (bolo "band ho jao")'); return; }
      if (m.serverContent) handleContent(m.serverContent);
      if (m.toolCall) handleTools(m.toolCall.functionCalls || []);
      if (m.sessionResumptionUpdate && m.sessionResumptionUpdate.resumable && m.sessionResumptionUpdate.newHandle)
        resumeHandle = m.sessionResumptionUpdate.newHandle;
      if (m.goAway) { try { ws.close(4000, 'goaway') } catch (e) { } }   // connection jaane wala: turant handle ke saath naya
    };
    ws.onclose = (ev) => {
      const failedSetup = !setupDone;
      ws = null; setupDone = false;
      if (failedSetup) { lastErr = (cfg.auth || ['key'])[authIdx] + '/' + cfg.models[Math.min(modelIdx, cfg.models.length - 1)] + ': ' + (ev.reason || ev.code); liveLog(lastErr); }
      if (!wantOn) return;
      if (failedSetup && resumeHandle) { resumeHandle = null; return connect(); }   // purana handle expire: naya session usi model par
      if (failedSetup && useGS) { useGS = false; return connect(); }                  // model Google khoj ke saath na chale to uske bina
      if (failedSetup && modelIdx < cfg.models.length - 1) { modelIdx++; say('step', '⚙ dusra Live model try: ' + cfg.models[modelIdx]); return connect(); }
      if (failedSetup && authIdx < (cfg.auth || ['key']).length - 1) {   // is tareeke se koi model nahi chala: doosra tareeka (token -> key)
        authIdx++; modelIdx = 0; useGS = true; resumeHandle = null; say('step', '⚙ Live ka doosra raasta try'); return connect();
      }
      if (failedSetup) { say('ai', 'Live mode nahi chal paaya (' + lastErr + '). Purane mode mein chal raha hoon. Ye galti errors.log mein likh di hai.'); L.stop(true); if (window.goLive) window.goLive(true); return; }
      if (reconnects++ < 20) setTimeout(() => wantOn && connect(), 600);   // session time limit: chupchaap naya session
    };
  }

  let curUser = '', curAi = '', camTimer = null, toolsThisTurn = 0, fixes = 0;
  async function heard(who, text) {   // baat server tak: yaad, mood, sankat ki pehchaan
    if (!text.trim()) return;
    try {
      const r = await fetch('/api/heard', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Pin': window.VPIN || '', 'X-Visual-Token': window.VTOKEN || '' },
        body: JSON.stringify({ who, text }) }).then(r => r.json());
      if (r.mood && window.setMood) window.setMood(r.mood);
      if (r.note && ws && ws.readyState === 1) ws.send(JSON.stringify({ realtimeInput: { text: r.note } }));
    } catch (e) { }
  }
  function handleContent(sc) {
    if (sc.interrupted) { stopPlayback(); }
    const parts = (sc.modelTurn && sc.modelTurn.parts) || [];
    for (const p of parts) if (p.inlineData && p.inlineData.data) playPCM(unb64(p.inlineData.data));
    if (sc.inputTranscription && sc.inputTranscription.text) {
      const t = sc.inputTranscription.text; curUser += t;
      if (!userLine) { userLine = document.createElement('div'); userLine.className = 'msg me'; document.getElementById('log').appendChild(userLine); userLine.textContent = ''; }
      userLine.textContent += t;
      if (/(band ho ja|band karo|so jao|बंद हो ज|बंद करो|सो जाओ)/i.test(userLine.textContent)) { setTimeout(() => L.stop(), 1500); }
    }
    if (sc.outputTranscription && sc.outputTranscription.text) {
      if (curUser) { heard('user', curUser); curUser = ''; }
      if (!aiLine) { aiLine = document.createElement('div'); aiLine.className = 'msg ai'; document.getElementById('log').appendChild(aiLine); aiLine.textContent = ''; userLine = null; }
      aiLine.textContent += sc.outputTranscription.text; curAi += sc.outputTranscription.text;
    }
    if (sc.turnComplete) {
      if (curUser) { heard('user', curUser); curUser = ''; }
      // SACHCHAI JAANCH: kaam karne ka daava kiya par koi tool nahi chala = jhooth. Turant sudharwao.
      // kaam ka shabd + 'ho gaya/kar diya/kar raha/karunga' paas-paas ho tabhi daava maano ("shaam ho gayi" jaisi baat par nahi)
      const claim = /(delete|डिलीट|mita|मिटा|upgrade|अपग्रेड|update|अपडेट|install|इंस्टॉल|bana|बना|bhej|भेज|khol|खोल|call|कॉल|save|सेव|set |सेट|chalu|चालू|band|बंद|jod|जोड़|fix|ठीक|sudhaar|सुधार|deploy|डिप्लॉय|push|पुश)[^.!?।\n]{0,30}(kar diya|kar di(?![a-z])|diya|दिया|कर दी|ho gaya|ho gayi|हो गया|हो गई|kar raha|kar rahi|कर रहा|कर रही|karunga|karungi|करूँगा|करूंगा|कर दूँगा|कर दूंगा|kar dunga|shuru|शुरू)/i;
      if (curAi && claim.test(curAi) && toolsThisTurn === 0 && fixes < 2) {
        fixes++;
        say('step', '⚠ VISUAL ne bina kaam kiye daava kiya, sudharwa raha hoon');
        if (ws && ws.readyState === 1) ws.send(JSON.stringify({ realtimeInput: { text:
          '[SACHCHAI JAANCH] Tumne abhi kaha "' + curAi.slice(0, 120) + '" par koi tool nahi chala, yani asal mein kuch nahi hua. ' +
          'Abhi sahi tool chalao (bada kaam ho to agent_task, delete ho to delete wala tool). Agar aisa tool hai hi nahi to owner ko saaf bolo ' +
          '"ye main abhi nahi kar sakta". Bina tool ke kabhi mat kaho ki kaam ho gaya.' } }));
      } else if (toolsThisTurn > 0) fixes = 0;
      if (curAi) { heard('visual', curAi); curAi = ''; }
      toolsThisTurn = 0;
      userLine = null; aiLine = null;
    }
    const log = document.getElementById('log'); if (log) log.scrollTop = log.scrollHeight;
  }
  function camLoop(on) {   // camera chalu ho to har second ek tasveer Live ko (dekh kar baat)
    clearInterval(camTimer); camTimer = null;
    if (!on) return;
    camTimer = setInterval(() => {
      try {
        if (!(ws && ws.readyState === 1 && setupDone)) return;
        if (typeof camStream === 'undefined' || !camStream || typeof grab !== 'function') return;
        const img = grab(); if (img && img.length > 100) ws.send(JSON.stringify({ realtimeInput: { video: { data: img.split(',')[1], mimeType: 'image/jpeg' } } }));
      } catch (e) { }
    }, 1000);
  }

  async function confirmAsk(name, args) {
    return new Promise(res => {
      const d = document.createElement('div');
      d.style.cssText = 'position:fixed;inset:0;background:#000c;display:grid;place-items:center;z-index:10;color:#fff;text-align:center;padding:20px';
      d.innerHTML = '<div><div style="font-size:18px;margin-bottom:14px">VISUAL ye karna chahta hai:</div><b style="color:var(--c)">' + name + '</b><pre style="white-space:pre-wrap;font-size:13px;max-width:90vw">' +
        JSON.stringify(args, null, 1).replace(/[<>&]/g, '') + '</pre><button id="cy" style="font-size:20px;padding:12px 26px;margin:8px;border-radius:12px">✅ Haan</button><button id="cn" style="font-size:20px;padding:12px 26px;margin:8px;border-radius:12px">❌ Nahi</button></div>';
      document.body.appendChild(d);
      d.querySelector('#cy').onclick = () => { d.remove(); res(true) }; d.querySelector('#cn').onclick = () => { d.remove(); res(false) };
    });
  }

  async function handleTools(calls) {
    toolsThisTurn += calls.length;
    const responses = [];
    for (const c of calls) {
      say('step', '⚙ ' + c.name);
      let out;
      try {
        if (cfg.risky.includes(c.name) && !(await confirmAsk(c.name, c.args || {}))) out = { result: 'Owner ne mana kar diya. Ye kaam mat karo.' };
        else {
          const r = await fetch('/api/tool', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Pin': window.VPIN || '', 'X-Visual-Token': window.VTOKEN || '' },
            body: JSON.stringify({ name: c.name, args: c.args || {} }) }).then(r => r.json());
          out = { result: r.result };
          for (const img of (r.images || [])) {   // camera/screen ki tasveer model ko dikhao
            if (ws && ws.readyState === 1) ws.send(JSON.stringify({ realtimeInput: { video: { data: img.split(',')[1], mimeType: 'image/jpeg' } } }));
          }
          if (r.mood && window.setMood) window.setMood(r.mood);
          if (r.restart) setTimeout(() => L.refresh(), 7000);   // VISUAL ne khud ko upgrade kiya: naye tools ke saath dobara judo
        }
      } catch (e) { out = { error: String(e) } }
      responses.push({ name: c.name, id: c.id, response: out });
    }
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ toolResponse: { functionResponses: responses } }));
  }

  L.available = async function () {
    try { cfg = await fetch('/api/live/config', { headers: { 'X-Pin': window.VPIN || '', 'X-Visual-Token': window.VTOKEN || '' } }).then(r => r.json()); return !!(cfg && cfg.ok); }
    catch (e) { return false }
  };
  L.announce = function (text) {   // Engineer ka kaam pura: Live model owner ko bolkar bataye
    if (ws && ws.readyState === 1 && setupDone) { ws.send(JSON.stringify({ realtimeInput: { text: '[ENGINEER REPORT] ' + text.slice(0, 3000) } })); return true; }
    return false;
  };
  L.refresh = async function () {
    for (let i = 0; i < 10; i++) { cfg = null; if (await L.available()) break; await new Promise(r => setTimeout(r, 1500)); }
    say('step', '⚙ VISUAL upgrade ho gaya, naye kaam ke saath dobara jud raha hoon');
    try { ws && ws.close() } catch (e) { }
  };
  L.start = async function () {
    if (!cfg) await L.available();
    if (!cfg || !cfg.ok) return false;
    wantOn = true; L.on = true; modelIdx = 0; reconnects = 0; resumeHandle = null; useGS = true; authIdx = 0;
    try { await startMic(); } catch (e) { say('ai', 'Mic nahi khula: ' + e.message + '. Chrome mein mic Allow karo.'); L.stop(); return false; }
    if (!outCtx) outCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    try { outCtx.resume() } catch (e) { }
    connect(); camLoop(true);
    ui('thinking', 'LIVE jud raha hai...');
    if (window.keepAwake) window.keepAwake(true);
    return true;
  };
  L.stop = function (silent) {
    wantOn = false; L.on = false; stopPlayback(); stopMic(); camLoop(false);
    try { ws && ws.close() } catch (e) { } ws = null;
    if (window.keepAwake) window.keepAwake(false);
    const m = document.getElementById('mic'); if (m) m.classList.remove('on');
    ui('', 'mic ek baar dabao, LIVE baat shuru');
    if (!silent) say('ai', 'Theek hai, LIVE band. Mic dabao to phir shuru.');
  };
})();
