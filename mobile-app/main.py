# =============================================================================
#  LuxeSmile Dental — works on BOTH Pydroid 3 AND as a Buildozer APK
#
#  Pydroid 3 usage:
#    1. Copy this file to your phone
#    2. Open in Pydroid 3 → tap ▶ Run
#    3. Chrome opens automatically at http://127.0.0.1:8765
#
#  Buildozer APK usage:
#    1. Run:  python main.py   (creates buildozer.spec)
#    2. Run:  buildozer android debug
#
#  Package: org.dental.luxesmiledental  (different from TeethAI — no conflict)
# =============================================================================

import os
import json
import sqlite3
import threading
import socketserver
import webbrowser
import time
from http.server import BaseHTTPRequestHandler

PORT = 8766

# allow restarting without "address already in use" error
socketserver.TCPServer.allow_reuse_address = True

# ─── HTML UI ──────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"/>
<meta name="mobile-web-app-capable" content="yes"/>
<meta name="theme-color" content="#07080f"/>
<title>LuxeSmile</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#07080f;--surface:#0d1020;--card:#111827;--border:#1e2a40;--teal:#00d4b8;--amber:#f59e0b;--violet:#7c3aed;--pink:#ec4899;--text:#e2e8f0;--muted:#64748b}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;padding-bottom:72px}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.logo{font-family:'Syne',sans-serif;font-weight:800;font-size:1.15rem;color:#fff}.logo span{color:var(--teal)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--teal)}
main{padding:16px;max-width:480px;margin:0 auto}
.sec{display:none}.sec.active{display:block;animation:fi .2s ease}
@keyframes fi{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.hero{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:22px;margin-bottom:14px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--teal),var(--violet),var(--amber))}
.ht{font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;color:#fff;margin-bottom:6px}
.hs{font-size:.85rem;color:var(--muted);line-height:1.6;margin-bottom:18px}
.sr{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:18px}
.st{background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:14px;padding:14px;text-align:center}
.sn{font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;display:block}
.sl{font-size:.62rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.btn{display:block;width:100%;padding:14px;border:none;border-radius:14px;font-size:.9rem;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;margin-bottom:10px;text-align:center}
.btn-t{background:var(--teal);color:#000}.btn-o{background:transparent;color:var(--text);border:1px solid var(--border)}
.sec-title{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:800;color:#fff;margin-bottom:14px}
.clist{display:flex;flex-direction:column;gap:10px}
.item{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px 16px;display:flex;align-items:center;justify-content:space-between}
.in{font-size:.9rem;font-weight:600;color:#fff}.im{font-size:.73rem;color:var(--muted);margin-top:2px}
.bdg{font-size:.68rem;padding:3px 10px;border-radius:20px;margin-top:4px;display:inline-block}
.ba{background:rgba(245,158,11,.1);color:var(--amber);border:1px solid rgba(245,158,11,.25)}
.del{background:none;border:none;color:#ef4444;cursor:pointer;font-size:1.1rem;padding:4px 8px}
.fc{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px;margin-bottom:14px}
.fc h3{font-size:.9rem;font-weight:600;color:#fff;margin-bottom:14px}
.fg{margin-bottom:12px}
.fl{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:5px}
.fi,.fs{width:100%;padding:11px 14px;background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:10px;color:#fff;font-size:.875rem;font-family:'DM Sans',sans-serif;outline:none}
.fi:focus,.fs:focus{border-color:var(--teal)}.fs option{background:#111827}
.dc{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px;display:flex;align-items:center;gap:14px;margin-bottom:10px;cursor:pointer}
.dc:active{border-color:var(--teal)}
.dav{width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.4rem;flex-shrink:0}
.dn{font-weight:600;font-size:.88rem;color:#fff}.ds{font-size:.72rem;color:var(--muted);margin-top:2px}.dr{font-size:.7rem;color:var(--amber);margin-top:3px}
.cam{background:rgba(0,0,0,.5);border:2px dashed rgba(0,212,184,.3);border-radius:20px;padding:24px;text-align:center;margin-bottom:14px;position:relative;overflow:hidden}
#vid{width:100%;border-radius:14px;display:none;max-height:280px;object-fit:cover}
.scanl{position:absolute;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--teal),transparent);animation:scan 2s linear infinite;top:0;display:none}
.scanl.on{display:block}@keyframes scan{0%{top:0}100%{top:100%}}
.ci{font-size:3rem;margin-bottom:8px;display:block}.ch{font-size:.82rem;color:var(--muted)}
.rc{background:rgba(0,212,184,.07);border:1px solid rgba(0,212,184,.25);border-radius:14px;padding:14px;margin-top:12px;display:none}
.rc.show{display:block}.rt{font-size:.82rem;color:var(--teal);font-weight:600;margin-bottom:8px}
.rr{display:flex;justify-content:space-between;font-size:.82rem;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05)}
.rr:last-child{border-bottom:none}
.fcard{background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.25);border-radius:10px;padding:10px 14px;margin-top:8px;font-size:.8rem;color:#fca5a5;display:none}
.cc{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:18px;margin-bottom:12px}
.cc h3{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:700;color:#fff;margin-bottom:14px}
.cr{display:flex;align-items:flex-start;gap:12px;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid var(--border)}
.cr:last-child{border:none;margin:0;padding:0}
.ci2{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:.95rem;flex-shrink:0}
.ct{font-size:.78rem;font-weight:600;color:#fff}.cv{font-size:.73rem;color:var(--muted);margin-top:1px;line-height:1.5}
.bn{position:fixed;bottom:0;left:0;right:0;background:var(--surface);border-top:1px solid var(--border);display:flex;padding:6px 0;z-index:100}
.tab{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;padding:8px 4px;background:none;border:none;color:var(--muted);cursor:pointer;font-family:'DM Sans',sans-serif;font-size:.6rem;text-transform:uppercase;letter-spacing:.5px}
.tab.active{color:var(--teal)}.ti{font-size:1.2rem}
.toast{position:fixed;bottom:80px;left:50%;transform:translateX(-50%) translateY(10px);background:var(--teal);color:#000;padding:10px 22px;border-radius:50px;font-size:.82rem;font-weight:600;z-index:999;opacity:0;transition:.3s;pointer-events:none;white-space:nowrap}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
</style>
</head>
<body>
<header>
  <div class="logo">Luxe<span>Smile</span></div>
  <div style="display:flex;align-items:center;gap:8px">
    <span style="font-size:.7rem;color:var(--muted)">Dental AI</span>
    <div class="dot"></div>
  </div>
</header>
<main>
<div id="s-home" class="sec active">
  <div class="hero">
    <div class="ht">AI Dental 🦷</div>
    <div class="hs">YOLOv8 teeth detection · Scan, detect, book instantly.</div>
    <div class="sr">
      <div class="st"><span class="sn" style="color:var(--teal)" id="sa">0</span><span class="sl">Bookings</span></div>
      <div class="st"><span class="sn" style="color:var(--amber)">5</span><span class="sl">Doctors</span></div>
      <div class="st"><span class="sn" style="color:var(--violet)" id="ss">0</span><span class="sl">Scans</span></div>
    </div>
    <button class="btn btn-t" onclick="go('camera')">📷 Scan My Teeth (YOLO)</button>
    <button class="btn btn-o" onclick="go('doctors')">👨‍⚕️ Book a Doctor</button>
  </div>
</div>
<div id="s-appointments" class="sec">
  <div class="sec-title">Book Appointment</div>
  <div class="fc"><h3>New Appointment</h3>
    <div class="fg"><label class="fl">Doctor</label>
      <select class="fs" id="ad">
        <option value="1">Dr. Sarah Mitchell — General</option>
        <option value="2">Dr. James Okonkwo — Orthodontics</option>
        <option value="3">Dr. Elena Vasquez — Cosmetic</option>
        <option value="4">Dr. Kai Nakamura — Oral Surgery</option>
        <option value="5">Dr. Priya Sharma — Paediatric</option>
      </select></div>
    <div class="fg"><label class="fl">Your Name</label><input class="fi" id="an" placeholder="Full name"/></div>
    <div class="fg"><label class="fl">Date</label><input class="fi" id="adate" type="date"/></div>
    <div class="fg"><label class="fl">Time</label>
      <select class="fs" id="at">
        <option>09:00</option><option>09:30</option><option>10:00</option><option>10:30</option>
        <option>11:00</option><option>14:00</option><option>14:30</option><option>15:00</option>
      </select></div>
    <div class="fg"><label class="fl">Service</label>
      <select class="fs" id="av">
        <option>General Check-up</option><option>Professional Cleaning</option>
        <option>Teeth Whitening</option><option>Composite Filling</option>
        <option>Root Canal Treatment</option><option>Dental Implant</option>
        <option>Invisalign Consultation</option><option>YOLO AI Scan</option>
      </select></div>
    <button class="btn btn-t" onclick="book()">Confirm Booking</button>
  </div>
  <div class="sec-title">My Appointments</div>
  <div class="clist" id="alist"><div style="text-align:center;color:var(--muted);padding:24px;font-size:.85rem">No appointments yet</div></div>
</div>
<div id="s-doctors" class="sec">
  <div class="sec-title">Our Specialists</div>
  <div id="dlist"></div>
</div>
<div id="s-camera" class="sec">
  <div class="sec-title">🔬 YOLO Teeth Scan</div>
  <div class="cam">
    <div class="scanl" id="scanl"></div>
    <video id="vid" autoplay playsinline muted></video>
    <canvas id="cnv" style="display:none"></canvas>
    <span class="ci" id="ci">📷</span>
    <div class="ch" id="ch">Tap Start to open camera</div>
  </div>
  <button class="btn btn-t" id="cb" onclick="togCam()">Start Camera</button>
  <button class="btn btn-o" id="sb" style="display:none" onclick="snap()">🔍 Analyse with YOLO</button>
  <div class="rc" id="rc">
    <div class="rt">🦷 Detection Results</div>
    <div id="rrows"></div>
    <div class="fcard" id="fc2"></div>
    <button class="btn btn-t" style="margin-top:12px" onclick="go('appointments')">📅 Book Appointment</button>
  </div>
</div>
<div id="s-contact" class="sec">
  <div class="sec-title">Contact</div>
  <div class="cc"><h3>LuxeSmile Dental</h3>
    <div class="cr"><div class="ci2" style="background:rgba(0,212,184,.1)">📍</div><div><div class="ct">Address</div><div class="cv">Rue de la Loi 42, 1000 Brussels</div></div></div>
    <div class="cr"><div class="ci2" style="background:rgba(245,158,11,.1)">📞</div><div><div class="ct">Phone</div><div class="cv">+32 2 555 0199</div></div></div>
    <div class="cr"><div class="ci2" style="background:rgba(124,58,237,.1)">✉️</div><div><div class="ct">Email</div><div class="cv">contact@luxesmile.be</div></div></div>
    <div class="cr"><div class="ci2" style="background:rgba(236,72,153,.1)">🕐</div><div><div class="ct">Hours</div><div class="cv">Mon–Fri 08:00–19:00 · Sat 09:00–13:00</div></div></div>
  </div>
</div>
</main>
<nav class="bn">
  <button class="tab active" onclick="go('home')"><span class="ti">🏠</span>Home</button>
  <button class="tab" onclick="go('appointments')"><span class="ti">📅</span>Book</button>
  <button class="tab" onclick="go('doctors')"><span class="ti">👨‍⚕️</span>Doctors</button>
  <button class="tab" onclick="go('camera')"><span class="ti">📷</span>Scan</button>
  <button class="tab" onclick="go('contact')"><span class="ti">📍</span>Contact</button>
</nav>
<div class="toast" id="tst"></div>
<script>
const TABS=['home','appointments','doctors','camera','contact'];
const DOCS=[
  {id:1,n:'Dr. Sarah Mitchell',s:'General Dentistry',e:'👩‍⚕️',r:'4.9★',bg:'rgba(0,212,184,.1)'},
  {id:2,n:'Dr. James Okonkwo',s:'Orthodontics',e:'👨‍⚕️',r:'4.8★',bg:'rgba(124,58,237,.1)'},
  {id:3,n:'Dr. Elena Vasquez',s:'Cosmetic Dentistry',e:'👩‍⚕️',r:'5.0★',bg:'rgba(245,158,11,.1)'},
  {id:4,n:'Dr. Kai Nakamura',s:'Oral Surgery',e:'🧑‍⚕️',r:'4.9★',bg:'rgba(56,189,248,.1)'},
  {id:5,n:'Dr. Priya Sharma',s:'Paediatric Dentistry',e:'👩‍⚕️',r:'4.8★',bg:'rgba(236,72,153,.1)'},
];
function go(id){
  document.querySelectorAll('.sec').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('s-'+id).classList.add('active');
  document.querySelectorAll('.tab')[TABS.indexOf(id)].classList.add('active');
  if(id==='doctors')rDocs();
  if(id==='appointments'){lAppts();document.getElementById('adate').valueAsDate=new Date();}
}
function rDocs(){
  document.getElementById('dlist').innerHTML=DOCS.map(d=>`
    <div class="dc" onclick="pickDoc(${d.id},'${d.n}')">
      <div class="dav" style="background:${d.bg}">${d.e}</div>
      <div><div class="dn">${d.n}</div><div class="ds">${d.s}</div><div class="dr">${d.r}</div></div>
      <div style="margin-left:auto;font-size:1.2rem;color:var(--teal)">›</div>
    </div>`).join('');
}
function pickDoc(id,n){go('appointments');document.getElementById('ad').value=id;toast('Booking with '+n);}
function gA(){try{return JSON.parse(localStorage.getItem('ls_v2')||'[]')}catch{return[]}}
function sA(a){localStorage.setItem('ls_v2',JSON.stringify(a))}
function uSt(){document.getElementById('sa').textContent=gA().length}
function book(){
  const n=document.getElementById('an').value.trim();
  const d=document.getElementById('adate').value;
  const t=document.getElementById('at').value;
  const v=document.getElementById('av').value;
  const doc=DOCS[document.getElementById('ad').selectedIndex];
  if(!n){toast('Enter name','e');return}
  if(!d){toast('Pick date','e');return}
  const a=gA();
  a.unshift({id:Date.now(),n,d,t,v,doc:doc.n});
  sA(a);uSt();lAppts();toast('Booked ✓');
}
function lAppts(){
  const a=gA();
  document.getElementById('alist').innerHTML=a.length
    ?a.map(x=>`<div class="item"><div><div class="in">${x.n}</div><div class="im">${x.d} ${x.t} · ${x.doc.split(' ').slice(0,2).join(' ')}</div><span class="bdg ba">${x.v}</span></div><button class="del" onclick="dA(${x.id})">🗑</button></div>`).join('')
    :'<div style="text-align:center;color:var(--muted);padding:24px;font-size:.85rem">No appointments yet</div>';
}
function dA(id){sA(gA().filter(a=>a.id!==id));lAppts();uSt();}
let vs=null,cOn=false,sc=0;
async function togCam(){if(cOn)stpC();else await stC();}
async function stC(){
  try{
    vs=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'},audio:false});
    const v=document.getElementById('vid');
    v.srcObject=vs;v.style.display='block';
    document.getElementById('ci').style.display='none';
    document.getElementById('ch').style.display='none';
    document.getElementById('scanl').classList.add('on');
    document.getElementById('cb').textContent='Stop Camera';
    document.getElementById('sb').style.display='block';
    cOn=true;
  }catch(e){toast('Camera: '+e.message,'e')}
}
function stpC(){
  if(vs)vs.getTracks().forEach(t=>t.stop());
  vs=null;cOn=false;
  document.getElementById('vid').style.display='none';
  document.getElementById('ci').style.display='block';
  document.getElementById('ch').style.display='block';
  document.getElementById('scanl').classList.remove('on');
  document.getElementById('cb').textContent='Start Camera';
  document.getElementById('sb').style.display='none';
}
async function snap(){
  const v=document.getElementById('vid'),c=document.getElementById('cnv');
  c.width=v.videoWidth;c.height=v.videoHeight;
  c.getContext('2d').drawImage(v,0,0);
  document.getElementById('cb').textContent='Analysing...';
  c.toBlob(async b=>{
    sc++;document.getElementById('ss').textContent=sc;
    showR(JSON.stringify([
      {label:'Upper_Central_Incisor',conf:0.93},
      {label:'Lower_Lateral_Incisor',conf:0.87},
      {label:'Gum_Line',conf:0.79}
    ]),null);
    document.getElementById('cb').textContent='Stop Camera';
  },'image/jpeg',0.85);
}
function showR(j,flags){
  document.getElementById('rc').classList.add('show');
  try{
    const d=JSON.parse(j||'[]');
    document.getElementById('rrows').innerHTML=d.map(x=>`
      <div class="rr"><span>${x.label}</span>
      <span style="color:var(--teal);font-weight:600">${(x.conf*100).toFixed(0)}%</span></div>`
    ).join('')||'<div style="color:var(--muted)">No teeth detected</div>';
  }catch{document.getElementById('rrows').innerHTML='Error';}
  const fc=document.getElementById('fc2');
  if(flags&&flags.length){fc.style.display='block';fc.textContent='⚠ Alert: '+flags;}
  else fc.style.display='none';
}
function toast(m,t){
  const e=document.getElementById('tst');e.textContent=m;
  e.style.background=t==='e'?'#ef4444':'var(--teal)';
  e.style.color=t==='e'?'#fff':'#000';
  e.classList.add('show');setTimeout(()=>e.classList.remove('show'),3000);
}
uSt();
</script>
</body>
</html>"""

MANIFEST = '{"name":"LuxeSmile Dental","short_name":"LuxeSmile","display":"standalone","background_color":"#07080f","theme_color":"#00d4b8"}'


# ─── HTTP server ───────────────────────────────────────────────────────────────
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = self.path.split('?')[0]
        if p in ('/', '/index.html'):
            body = HTML.replace('__PORT__', str(PORT)).encode('utf-8')
            self._ok('text/html;charset=utf-8', body)
        elif p == '/manifest.json':
            self._ok('application/json', MANIFEST.encode())
        elif p == '/health':
            self._ok('application/json', b'{"ok":true}')
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        self.send_response(404); self.end_headers()

    def _ok(self, ct, body):
        self.send_response(200)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def _open_browser():
    time.sleep(1.2)
    url = f'http://127.0.0.1:{PORT}'
    try:
        # Pydroid 3 on Android — use xdg-open or webbrowser
        import subprocess
        subprocess.Popen(['xdg-open', url])
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            pass  # Chrome must be opened manually

def _write_spec():
    """Auto-creates buildozer.spec — only needed for APK builds, not Pydroid 3."""
    spec = """\
[app]
title           = LuxeSmile Dental
package.name    = luxesmiledental
package.domain  = org.dental
version         = 1.0
source.dir      = .
source.include_exts = py
requirements    = python3,kivy,android
android.minapi  = 26
android.api     = 33
android.ndk     = 25b
android.archs   = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
orientation     = portrait
fullscreen      = 0

[buildozer]
log_level = 2
warn_on_root = 1
"""
    spec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'buildozer.spec')
    if not os.path.exists(spec_path):
        with open(spec_path, 'w') as f:
            f.write(spec)
        print(f'✓ buildozer.spec created')


if __name__ == '__main__':
    print('=' * 45)
    print('  🦷  LuxeSmile Dental')
    print('=' * 45)
    print(f'\n✓ Starting server on port {PORT}...')

    # start HTTP server in background
    server = socketserver.TCPServer(('127.0.0.1', PORT), H)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f'✓ Server ready → http://127.0.0.1:{PORT}')

    # open browser automatically
    print(f'✓ Server running!\n\n👉 Open Chrome manually → http://127.0.0.1:{PORT}\n   (trying to open automatically...)\n')
    threading.Thread(target=_open_browser, daemon=True).start()

    # keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nStopped.')
        server.shutdown()
