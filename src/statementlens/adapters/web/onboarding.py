"""Onboarding page — the first-run experience, served when there is no data yet.

Three ways in, in order of how many people they work for:

1. **Drop PDFs** — works for everyone, every bank, every country, no accounts, no approvals.
2. **Pick a folder** — same, for people who already file statements somewhere.
3. **Connect Gmail** — one click, but capped at 100 users until Google's CASA assessment passes,
   because `gmail.readonly` is a restricted scope. Presented honestly rather than hidden.

The identity fields (name / DOB / mobile / card last-4) exist only to DERIVE statement passwords
locally — banks build the password out of them. They are never uploaded; the text on the page says
so, because asking for a date of birth without explaining why is how you lose a user's trust.
"""

from __future__ import annotations

import html

_PAGE = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>StatementLens · set up</title><link rel="icon" href="data:,">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Instrument+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#08080a;--s1:#101013;--s2:#17171b;--ink:#f4f4f0;--ink2:#9a9aa2;--ink3:#5c5c64;
  --line:rgba(255,255,255,.08);--acc:#c6f24e;--up:#8fe08f;--down:#ff8f8f;
  --disp:'Fraunces',Georgia,serif;--body:'Instrument Sans',system-ui,sans-serif;--ease:cubic-bezier(.2,.7,.3,1)}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#050507;color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.55;
  display:flex;justify-content:center;-webkit-font-smoothing:antialiased}
.app{width:100%;max-width:560px;background:var(--bg);min-height:100vh;padding:44px 24px 70px;
  background-image:radial-gradient(60% 30% at 50% 0%,rgba(198,242,78,.07),transparent 62%)}
h1{font:500 34px/1.1 var(--disp);letter-spacing:-.01em;margin-bottom:10px}
.lede{color:var(--ink2);margin-bottom:8px}
.priv{font-size:13px;color:var(--ink3);border-left:2px solid var(--acc);padding-left:11px;margin:20px 0 30px}
h2{font:500 15px/1 var(--disp);font-style:italic;margin:0 0 12px}
.card{background:var(--s1);border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:16px}
.drop{border:1.5px dashed var(--line);border-radius:16px;padding:34px 20px;text-align:center;
  cursor:pointer;transition:all .2s var(--ease)}
.drop.hot{border-color:var(--acc);background:rgba(198,242,78,.05)}
.drop b{display:block;font:500 17px/1.3 var(--disp);margin-bottom:5px}
.drop span{font-size:13px;color:var(--ink3)}
.row{display:flex;gap:10px;flex-wrap:wrap}
label{display:block;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);margin-bottom:6px}
input[type=text]{width:100%;background:var(--s2);border:1px solid var(--line);border-radius:10px;
  color:var(--ink);font:400 14px var(--body);padding:11px 13px}
input:focus{outline:none;border-color:var(--acc)}
.f{flex:1;min-width:150px;margin-bottom:12px}
button{background:var(--acc);color:#08080a;border:none;border-radius:100px;padding:12px 22px;
  font:600 14px var(--body);cursor:pointer}
button.ghost{background:transparent;color:var(--ink2);border:1px solid var(--line)}
button:disabled{opacity:.5;cursor:default}
.hint{font-size:12.5px;color:var(--ink3);margin-top:9px}
.warn{font-size:12.5px;color:var(--ink2);background:rgba(255,143,143,.07);border:1px solid rgba(255,143,143,.25);
  border-radius:10px;padding:11px 13px;margin-top:12px}
.log{font:400 12.5px/1.6 ui-monospace,monospace;color:var(--ink2);background:var(--s2);
  border-radius:10px;padding:13px;margin-top:14px;white-space:pre-wrap;max-height:230px;overflow:auto;display:none}
.log.on{display:block}
.ok{color:var(--up)}.bad{color:var(--down)}
a{color:var(--acc)}
</style></head><body><div class="app">

<h1>Let's see your money.</h1>
<div class="lede">Point StatementLens at your bank statements and it does the rest — reading them,
tagging every transaction, and telling you what changed.</div>
<div class="priv">Everything happens on this computer. Your statements and the details below never
leave it, and there is no account to create.</div>

<h2>1 · your details</h2>
<div class="card">
  <div class="hint" style="margin:0 0 14px">Banks lock statement PDFs with a password built from
    these. We use them to unlock the files locally — nothing is uploaded or saved to disk.</div>
  <div class="row">
    <div class="f"><label>full name</label><input type="text" id="name" placeholder="As printed on the statement"></div>
    <div class="f"><label>date of birth</label><input type="text" id="dob" placeholder="DDMMYYYY"></div>
  </div>
  <div class="row">
    <div class="f"><label>mobile</label><input type="text" id="mobile" placeholder="10 digits"></div>
    <div class="f"><label>card last 4 <span style="text-transform:none">(optional)</span></label><input type="text" id="card_last4" placeholder="1234"></div>
  </div>
</div>

<h2>2 · bring in your statements</h2>
<div class="card">
  <div class="drop" id="drop">
    <b>Drop statement PDFs here</b>
    <span>or click to choose files · works with any bank</span>
    <input type="file" id="file" accept="application/pdf" multiple hidden>
  </div>
  <div class="hint">Already keep them in a folder? <a id="usefolder" href="#">Import a folder instead</a></div>
  <div id="folderrow" style="display:none;margin-top:12px">
    <label>folder path</label>
    <div class="row"><div class="f" style="margin:0"><input type="text" id="folder" placeholder="~/Documents/Statements"></div>
      <button class="ghost" id="scan">Import</button></div>
  </div>
  <div class="log" id="log"></div>
</div>

<div class="card">
  <h2 style="margin-bottom:8px">or connect Gmail</h2>
  <div class="hint" style="margin:0 0 12px">Finds statement emails automatically and keeps itself up
    to date. Read-only — StatementLens can never send or change anything.</div>
  <button class="ghost" id="gmail">Connect Gmail</button>
  <div class="warn">Google shows an “unverified app” warning for this, and it works for a limited
    number of people until their review completes. Dropping PDFs above has no such limit.</div>
</div>

<script>
const TOK=new URLSearchParams(location.search).get('t')||'';
const q=s=>document.querySelector(s), log=q('#log');
function say(msg,cls){log.classList.add('on');
  const s=document.createElement('div');if(cls)s.className=cls;s.textContent=msg;
  log.appendChild(s);log.scrollTop=log.scrollHeight;}
function hints(){const h={};['name','dob','mobile','card_last4'].forEach(k=>{
  const v=q('#'+k).value.trim();if(v)h[k]=v;});return h;}
function qs(extra){const p=new URLSearchParams({t:TOK,...extra});return p.toString();}

/* report what happened in plain language — a silent no-op is the worst outcome */
function report(r){
  if(r.error){say('✕ '+r.error,'bad');return;}
  if(r.inserted)say(`✓ imported ${r.inserted} transactions`,'ok');
  if(r.duplicate)say(`· ${r.duplicate} already imported`);
  (r.skipped||[]).forEach(s=>say('✕ '+s.message,'bad'));
  (r.errors||[]).forEach(e=>say('✕ '+e,'bad'));
  if(r.inserted||r.duplicate){say('opening your dashboard…','ok');
    setTimeout(()=>location.href='/?t='+encodeURIComponent(TOK),1200);}
  else if(!(r.skipped||[]).length&&!(r.errors||[]).length)say('nothing to import here','bad');
}

/* --- drag & drop upload --- */
const drop=q('#drop'),file=q('#file');
drop.onclick=()=>file.click();
['dragenter','dragover'].forEach(e=>drop.addEventListener(e,ev=>{
  ev.preventDefault();drop.classList.add('hot');}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{
  ev.preventDefault();drop.classList.remove('hot');}));
drop.addEventListener('drop',ev=>upload([...ev.dataTransfer.files]));
file.onchange=()=>upload([...file.files]);

async function upload(files){
  const pdfs=files.filter(f=>f.name.toLowerCase().endsWith('.pdf'));
  if(!pdfs.length)return say('✕ those are not PDF files','bad');
  for(const f of pdfs){
    say('reading '+f.name+' …');
    try{
      const r=await fetch('/api/upload?'+qs({filename:f.name,...hints()}),
        {method:'POST',body:await f.arrayBuffer()}).then(r=>r.json());
      report(r);
    }catch(e){say('✕ '+e,'bad');}
  }
}

/* --- folder import --- */
q('#usefolder').onclick=e=>{e.preventDefault();q('#folderrow').style.display='block';};
q('#scan').onclick=async()=>{
  const f=q('#folder').value.trim();
  if(!f)return say('✕ enter a folder path','bad');
  say('scanning '+f+' …');
  const r=await fetch('/api/ingest?'+qs({}),{method:'POST',
    body:JSON.stringify({folder:[f],hints:hints()})}).then(r=>r.json()).catch(e=>({error:String(e)}));
  report(r);
};

/* --- gmail --- */
q('#gmail').onclick=async()=>{
  const b=q('#gmail');b.disabled=true;b.textContent='Waiting for Google…';
  say('a browser tab will open for Google sign-in …');
  const r=await fetch('/api/gmail?'+qs({}),{method:'POST',
    body:JSON.stringify({hints:hints()})}).then(r=>r.json()).catch(e=>({error:String(e)}));
  b.disabled=false;b.textContent='Connect Gmail';
  report(r);
};
</script></div></body></html>"""


_GMAIL_UNAVAILABLE = """
  <div class="hint">Gmail isn't enabled in this build — import your PDFs above instead.
    (It needs a Google OAuth client; see <code>bundled_client.py</code>.)</div>"""


def render_onboarding(gmail_available: bool = True) -> str:
    """Render the setup page. Hides the Gmail button when this build has no OAuth client, since a
    button that can only ever error is worse than no button."""
    if gmail_available:
        return _PAGE
    return _PAGE.replace(
        '<button class="ghost" id="gmail">Connect Gmail</button>', _GMAIL_UNAVAILABLE.strip())
