# =============================================================================
#  LuxeSmile Dental — Pydroid 3 + Buildozer APK
#
#  Pydroid 3:
#    pip install pillow        (in Pydroid pip menu)
#    then tap ▶ Run
#    then open Chrome → http://localhost:8766
#
#  Buildozer APK:
#    python main.py   → creates buildozer.spec
#    buildozer android debug
# =============================================================================

import os, json, sqlite3, threading, socketserver, webbrowser, time, base64, io
from http.server import BaseHTTPRequestHandler

PORT = 8766
socketserver.ThreadingTCPServer.allow_reuse_address = True

# ── YOLO analysis (pure Python + Pillow — no OpenCV needed in Pydroid) ──────
def analyse_image(image_bytes):
    """
    Analyses a JPEG/PNG from the camera.
    Uses Pillow for color analysis (same LAB-style brightness logic as TeethAI).
    Returns list of tooth detections with color grade and edge info.
    """
    results = []
    flags   = []

    try:
        from PIL import Image, ImageFilter, ImageStat
        import math

        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        w, h = img.size

        # ── Crop centre region (where teeth usually appear) ────────────────
        margin_x = int(w * 0.15)
        margin_y = int(h * 0.25)
        roi = img.crop((margin_x, margin_y, w - margin_x, h - margin_y))
        roi_w, roi_h = roi.size

        # ── Edge detection via ImageFilter ────────────────────────────────
        grey      = roi.convert('L')
        edges     = grey.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_mean = edge_stat.mean[0]          # 0–255; higher = more edges

        edge_label = (
            'Sharp'    if edge_mean > 18 else
            'Moderate' if edge_mean > 9  else
            'Soft'
        )

        # ── Colour analysis (LAB-style brightness like TeethAI) ───────────
        # Convert to LAB approximation via luminance
        r_stat = ImageStat.Stat(roi)
        r_mean, g_mean, b_mean = r_stat.mean[:3]

        # Luminance (same formula as cv2 COLOR_BGR2LAB L channel)
        L = 0.299 * r_mean + 0.587 * g_mean + 0.114 * b_mean

        # Yellowness: how much more R+G than B (staining indicator)
        yellow = (r_mean + g_mean) / 2 - b_mean

        # Colour grade — same thresholds as TeethAI draw() function
        if L > 155:
            grade = 'Excellent'
            grade_color = '#00e676'
        elif L > 100:
            grade = 'Good'
            grade_color = '#00d4b8'
        elif L > 50:
            grade = 'Fair'
            grade_color = '#f59e0b'
        else:
            grade = 'Stained'
            grade_color = '#ef4444'

        # ── Simulate segmentation detections across ROI ───────────────────
        # Divide ROI into tooth-sized columns (like the segmentation mask approach)
        tooth_w = max(1, roi_w // 8)
        detected = []

        for i in range(8):
            x1 = i * tooth_w
            x2 = min((i + 1) * tooth_w, roi_w)
            patch = roi.crop((x1, 0, x2, roi_h))
            ps    = ImageStat.Stat(patch)
            pL    = 0.299*ps.mean[0] + 0.587*ps.mean[1] + 0.114*ps.mean[2]

            # confidence based on how bright/white this column is
            conf = min(0.99, max(0.40, pL / 255.0 * 1.3))

            # skip very dark patches (likely not teeth)
            if pL < 30:
                continue

            p_yellow = (ps.mean[0] + ps.mean[1]) / 2 - ps.mean[2]
            if p_yellow > 40:
                p_grade = 'Stained'
            elif pL > 155:
                p_grade = 'Excellent'
            elif pL > 100:
                p_grade = 'Good'
            else:
                p_grade = 'Fair'

            detected.append({
                'tooth':  i + 1,
                'conf':   round(conf, 2),
                'grade':  p_grade,
                'L':      round(pL, 1),
            })

        tooth_count = len(detected)

        if tooth_count == 0:
            flags.append('No_Teeth_Detected')
        elif tooth_count < 4:
            flags.append('Few_Teeth_Visible — open mouth wider')

        if yellow > 45:
            flags.append('Staining_Detected — whitening recommended')

        # ── Build result list ─────────────────────────────────────────────
        grade_map = {'Excellent': '#00e676', 'Good': '#00d4b8',
                     'Fair': '#f59e0b', 'Stained': '#ef4444'}

        results = [{
            'label':  f"Tooth {d['tooth']}",
            'conf':   d['conf'],
            'grade':  d['grade'],
            'color':  grade_map.get(d['grade'], '#aaa'),
        } for d in detected]

        # ── Summary row ───────────────────────────────────────────────────
        summary = {
            'label':       f"Overall: {grade}",
            'conf':        round(L / 255, 2),
            'grade':       grade,
            'color':       grade_color,
            'edge':        edge_label,
            'tooth_count': tooth_count,
            'luminance':   round(L, 1),
            'yellowness':  round(yellow, 1),
            'is_summary':  True,
        }
        results.insert(0, summary)

    except Exception as e:
        flags.append(f'Analysis_Error: {e}')
        results = [{'label': 'Error during analysis', 'conf': 0, 'grade': 'Unknown',
                    'color': '#ef4444', 'is_summary': True}]

    return results, flags


# ── HTML ──────────────────────────────────────────────────────────────────────
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
:root{--bg:#07080f;--surface:#0d1020;--card:#111827;--border:#1e2a40;--teal:#00d4b8;--amber:#f59e0b;--violet:#7c3aed;--text:#e2e8f0;--muted:#64748b}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;padding-bottom:80px}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:12px 18px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.logo{font-family:'Syne',sans-serif;font-weight:800;font-size:1.1rem;color:#fff}.logo span{color:var(--teal)}
main{padding:14px;max-width:480px;margin:0 auto}
.sec{display:none}.sec.active{display:block;animation:fi .2s ease}
@keyframes fi{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.hero{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:20px;margin-bottom:12px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--teal),var(--violet),var(--amber))}
.ht{font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;color:#fff;margin-bottom:5px}
.hs{font-size:.83rem;color:var(--muted);line-height:1.6;margin-bottom:16px}
.sr{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:16px}
.st{background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:12px;padding:12px;text-align:center}
.sn{font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;display:block}
.sl{font-size:.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.btn{display:block;width:100%;padding:13px;border:none;border-radius:12px;font-size:.88rem;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;margin-bottom:8px;text-align:center;transition:.2s}
.btn-t{background:var(--teal);color:#000}.btn-o{background:transparent;color:var(--text);border:1px solid var(--border)}
.btn-v{background:var(--violet);color:#fff}
.btn:active{opacity:.8}
.sec-title{font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:#fff;margin-bottom:12px}
/* Camera */
.cam-wrap{background:rgba(0,0,0,.6);border:2px dashed rgba(0,212,184,.3);border-radius:18px;overflow:hidden;margin-bottom:10px;position:relative;min-height:220px;display:flex;align-items:center;justify-content:center}
#vid{width:100%;display:none;max-height:300px;object-fit:cover}
#canvas{display:none}
.cam-ph{text-align:center;padding:30px 20px}
.cam-ph .icon{font-size:2.8rem;display:block;margin-bottom:8px}
.cam-ph p{font-size:.8rem;color:var(--muted)}
.scanl{position:absolute;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--teal),transparent);animation:scan 2s linear infinite;display:none}
.scanl.on{display:block}@keyframes scan{0%{top:0%}100%{top:100%}}
/* snap preview */
#snap-preview{width:100%;border-radius:14px;display:none;margin-bottom:10px;border:2px solid var(--teal)}
/* cam controls row */
.cam-ctrl{display:flex;gap:8px;margin-bottom:8px}
.cam-ctrl .btn{flex:1;margin:0}
/* Results */
.result-wrap{background:rgba(0,212,184,.06);border:1px solid rgba(0,212,184,.2);border-radius:14px;padding:14px;margin-bottom:10px;display:none}
.result-wrap.show{display:block}
.result-title{font-size:.8rem;color:var(--teal);font-weight:700;margin-bottom:10px}
.r-summary{background:rgba(255,255,255,.04);border-radius:10px;padding:12px;margin-bottom:10px}
.r-sum-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.r-sum-row:last-child{margin:0}
.r-label{font-size:.78rem;color:var(--muted)}
.r-val{font-size:.85rem;font-weight:700}
.r-grade{font-size:1rem;font-weight:800;font-family:'Syne',sans-serif}
.tooth-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:10px}
.tooth-card{background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:8px 4px;text-align:center}
.tooth-num{font-size:.65rem;color:var(--muted);display:block}
.tooth-g{font-size:.68rem;font-weight:700;display:block;margin-top:2px}
.tooth-c{font-size:.6rem;color:var(--muted);display:block}
.flag-wrap{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);border-radius:10px;padding:10px 12px;margin-bottom:10px;display:none}
.flag-wrap.show{display:block}
.flag-item{font-size:.78rem;color:#fca5a5;margin-bottom:3px}
.flag-item:last-child{margin:0}
/* Appointments */
.fc{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;margin-bottom:12px}
.fc h3{font-size:.88rem;font-weight:600;color:#fff;margin-bottom:12px}
.fg{margin-bottom:10px}
.fl{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:4px}
.fi,.fs{width:100%;padding:10px 12px;background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:9px;color:#fff;font-size:.85rem;font-family:'DM Sans',sans-serif;outline:none}
.fi:focus,.fs:focus{border-color:var(--teal)}.fs option{background:#111827}
.clist{display:flex;flex-direction:column;gap:8px}
.item{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;display:flex;align-items:center;justify-content:space-between}
.in{font-size:.88rem;font-weight:600;color:#fff}.im{font-size:.7rem;color:var(--muted);margin-top:2px}
.bdg{font-size:.65rem;padding:2px 8px;border-radius:20px;margin-top:3px;display:inline-block;background:rgba(245,158,11,.1);color:var(--amber);border:1px solid rgba(245,158,11,.25)}
.del{background:none;border:none;color:#ef4444;cursor:pointer;font-size:1rem;padding:4px 6px}
/* Doctors */
.dc{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;display:flex;align-items:center;gap:12px;margin-bottom:8px;cursor:pointer}
.dc:active{border-color:var(--teal)}
.doc-avatar{width:54px;height:54px;border-radius:50%;overflow:hidden;flex-shrink:0;background:rgba(255,255,255,.05);border:1px solid var(--border)}
.dphoto{width:100%;height:100%;object-fit:cover;display:block}
.dav{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:1.3rem}
.dn{font-weight:600;font-size:.86rem;color:#fff}.ds{font-size:.7rem;color:var(--muted);margin-top:2px}.dr{font-size:.68rem;color:var(--amber);margin-top:2px}
/* Contact */
.cc{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px;margin-bottom:10px}
.cr{display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.cr:last-child{border:none;margin:0;padding:0}
.ci2{width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:.9rem;flex-shrink:0}
.ct{font-size:.76rem;font-weight:600;color:#fff}.cv{font-size:.7rem;color:var(--muted);margin-top:1px;line-height:1.5}
/* Nav */
.bn{position:fixed;bottom:0;left:0;right:0;background:var(--surface);border-top:1px solid var(--border);display:flex;padding:5px 0;z-index:100}
.tab{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;padding:7px 4px;background:none;border:none;color:var(--muted);cursor:pointer;font-family:'DM Sans',sans-serif;font-size:.58rem;text-transform:uppercase;letter-spacing:.5px}
.tab.active{color:var(--teal)}.ti{font-size:1.1rem}
.toast{position:fixed;bottom:76px;left:50%;transform:translateX(-50%) translateY(10px);background:var(--teal);color:#000;padding:9px 20px;border-radius:50px;font-size:.8rem;font-weight:600;z-index:999;opacity:0;transition:.3s;pointer-events:none;white-space:nowrap}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.spinner{display:inline-block;width:16px;height:16px;border:2px solid rgba(0,212,184,.3);border-top-color:var(--teal);border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<header>
  <div class="logo">Luxe<span>Smile</span></div>
  <div style="font-size:.65rem;color:var(--muted)">AI Dental</div>
</header>
<main>

<!-- HOME -->
<div id="s-home" class="sec active">
  <div class="hero">
    <div class="ht">AI Dental 🦷</div>
    <div class="hs">Take a photo of your teeth · AI analyses colour &amp; edges · Book instantly.</div>
    <div class="sr">
      <div class="st"><span class="sn" style="color:var(--teal)" id="sa">0</span><span class="sl">Bookings</span></div>
      <div class="st"><span class="sn" style="color:var(--amber)">5</span><span class="sl">Doctors</span></div>
      <div class="st"><span class="sn" style="color:var(--violet)" id="ss">0</span><span class="sl">Scans</span></div>
    </div>
    <button class="btn btn-t" onclick="go('scan')">📷 Scan My Teeth</button>
    <button class="btn btn-o" onclick="go('appointments')">📅 Book Appointment</button>
  </div>
</div>

<!-- SCAN -->
<div id="s-scan" class="sec">
  <div class="sec-title">🔬 Teeth Scan &amp; Analysis</div>

  <!-- Camera view -->
  <div class="cam-wrap" id="cam-wrap">
    <div class="scanl" id="scanl"></div>
    <video id="vid" autoplay playsinline muted></video>
    <div class="cam-ph" id="cam-ph">
      <span class="icon">📷</span>
      <p>Tap "Start Camera" below<br>Open mouth, keep steady</p>
    </div>
  </div>

  <!-- Snap preview -->
  <img id="snap-preview" alt="captured"/>
  <canvas id="canvas"></canvas>

  <!-- Controls -->
  <div class="cam-ctrl">
    <button class="btn btn-t" id="btn-cam" onclick="toggleCam()">Start Camera</button>
    <button class="btn btn-o" id="btn-flip" onclick="flipCam()" style="display:none;max-width:52px;padding:13px 8px">🔄</button>
  </div>
  <button class="btn btn-v" id="btn-snap" onclick="takeSnap()" style="display:none">📸 Take Photo</button>
  <button class="btn btn-t" id="btn-analyse" onclick="analyseSnap()" style="display:none">🔍 Analyse with AI</button>
  <button class="btn btn-o" id="btn-retake" onclick="retake()" style="display:none">↩ Retake Photo</button>

  <!-- Flags -->
  <div class="flag-wrap" id="flag-wrap"></div>

  <!-- Results -->
  <div class="result-wrap" id="result-wrap">
    <div class="result-title">🦷 Analysis Results</div>
    <div class="r-summary" id="r-summary"></div>
    <div class="tooth-grid" id="tooth-grid"></div>
    <button class="btn btn-t" onclick="goBook()">📅 Book Appointment Now</button>
  </div>
</div>

<!-- APPOINTMENTS -->
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
    <div class="fg" id="scan-note-wrap" style="display:none">
      <label class="fl">Scan Result</label>
      <div class="fi" id="scan-note" style="font-size:.75rem;color:var(--teal);padding:8px 12px"></div>
    </div>
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
        <option>Invisalign Consultation</option><option>AI Scan Follow-up</option>
      </select></div>
    <button class="btn btn-t" onclick="book()">Confirm Booking</button>
  </div>
  <div class="sec-title">My Appointments</div>
  <div class="clist" id="alist"><div style="text-align:center;color:var(--muted);padding:20px;font-size:.83rem">No appointments yet</div></div>
</div>

<!-- DOCTORS -->
<div id="s-doctors" class="sec">
  <div class="sec-title">Our Specialists</div>
  <div id="dlist"></div>
</div>

<!-- CONTACT -->
<div id="s-contact" class="sec">
  <div class="sec-title">Contact</div>
  <div class="cc">
    <div class="cr"><div class="ci2" style="background:rgba(0,212,184,.1)">📍</div><div><div class="ct">Address</div><div class="cv">Rue de la Loi 42, 1000 Brussels</div></div></div>
    <div class="cr"><div class="ci2" style="background:rgba(245,158,11,.1)">📞</div><div><div class="ct">Phone</div><div class="cv">+32 2 555 0199</div></div></div>
    <div class="cr"><div class="ci2" style="background:rgba(124,58,237,.1)">✉️</div><div><div class="ct">Email</div><div class="cv">contact@luxesmile.be</div></div></div>
    <div class="cr"><div class="ci2" style="background:rgba(236,72,153,.1)">🕐</div><div><div class="ct">Hours</div><div class="cv">Mon–Fri 08:00–19:00 · Sat 09:00–13:00</div></div></div>
  </div>
</div>

</main>
<nav class="bn">
  <button class="tab active" onclick="go('home')"><span class="ti">🏠</span>Home</button>
  <button class="tab" onclick="go('scan')"><span class="ti">📷</span>Scan</button>
  <button class="tab" onclick="go('appointments')"><span class="ti">📅</span>Book</button>
  <button class="tab" onclick="go('doctors')"><span class="ti">👨‍⚕️</span>Doctors</button>
  <button class="tab" onclick="go('contact')"><span class="ti">📍</span>Contact</button>
</nav>
<div class="toast" id="tst"></div>

<script>
const TABS = ['home','scan','appointments','doctors','contact'];
const DOCS = [
  {id:1,n:'Dr. Sarah Mitchell',s:'General Dentistry',e:'👩‍⚕️',r:'4.9★',bg:'rgba(0,212,184,.1)',img:'/assets/doctors/sarah_mitchell.png'},
  {id:2,n:'Dr. James Okonkwo',s:'Orthodontics',e:'👨‍⚕️',r:'4.8★',bg:'rgba(124,58,237,.1)',img:'/assets/doctors/james_okonkwo.png'},
  {id:3,n:'Dr. Elena Vasquez',s:'Cosmetic Dentistry',e:'👩‍⚕️',r:'5.0★',bg:'rgba(245,158,11,.1)',img:'/assets/doctors/elena_vasquez.png'},
  {id:4,n:'Dr. Kai Nakamura',s:'Oral Surgery',e:'🧑‍⚕️',r:'4.9★',bg:'rgba(56,189,248,.1)',img:'/assets/doctors/kai_nakamura.png'},
  {id:5,n:'Dr. Priya Sharma',s:'Paediatric Dentistry',e:'👩‍⚕️',r:'4.8★',bg:'rgba(236,72,153,.1)',img:'/assets/doctors/priya_sharma.png'},
];

let lastScanSummary = '';

function go(id){
  document.querySelectorAll('.sec').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('s-'+id).classList.add('active');
  const idx = TABS.indexOf(id);
  if(idx>=0) document.querySelectorAll('.tab')[idx].classList.add('active');
  if(id==='doctors') rDocs();
  if(id==='scan' && !camOn) startCam();
  if(id==='appointments'){lAppts(); document.getElementById('adate').valueAsDate=new Date();}
}

// ── Camera ──────────────────────────────────────────────────────────────────
let stream = null;
let camOn  = false;
let facingMode = 'environment'; // start with back camera
let snapBlob = null;

async function toggleCam(){
  if(camOn) stopCam(); else await startCam();
}

async function startCam(){
  try{
    if(stream){ stream.getTracks().forEach(t=>t.stop()); stream=null; }
    stream = await navigator.mediaDevices.getUserMedia({
      video:{ facingMode: facingMode, width:{ideal:1280}, height:{ideal:720} },
      audio: false
    });
    const vid = document.getElementById('vid');
    vid.srcObject = stream;
    vid.style.display = 'block';
    document.getElementById('cam-ph').style.display = 'none';
    document.getElementById('scanl').classList.add('on');
    document.getElementById('btn-cam').textContent  = 'Stop Camera';
    document.getElementById('btn-flip').style.display = 'block';
    document.getElementById('btn-snap').style.display = 'block';
    document.getElementById('btn-analyse').style.display = 'none';
    document.getElementById('btn-retake').style.display = 'none';
    document.getElementById('snap-preview').style.display = 'none';
    camOn = true;
  } catch(e){
    toast('Camera error: ' + e.message, 'e');
  }
}

function stopCam(){
  if(stream) stream.getTracks().forEach(t=>t.stop());
  stream = null; camOn = false;
  document.getElementById('vid').style.display = 'none';
  document.getElementById('cam-ph').style.display = 'block';
  document.getElementById('scanl').classList.remove('on');
  document.getElementById('btn-cam').textContent   = 'Start Camera';
  document.getElementById('btn-flip').style.display  = 'none';
  document.getElementById('btn-snap').style.display  = 'none';
}

async function flipCam(){
  // Toggle between front and back camera
  facingMode = (facingMode === 'environment') ? 'user' : 'environment';
  if(camOn) await startCam();
  toast(facingMode === 'user' ? 'Front camera' : 'Back camera');
}

function takeSnap(){
  const vid = document.getElementById('vid');
  const can = document.getElementById('canvas');
  can.width  = vid.videoWidth  || 640;
  can.height = vid.videoHeight || 480;
  can.getContext('2d').drawImage(vid, 0, 0);

  can.toBlob(blob => {
    snapBlob = blob;
    // show preview
    const prev = document.getElementById('snap-preview');
    prev.src = URL.createObjectURL(blob);
    prev.style.display = 'block';
    // stop camera, show analyse button
    stopCam();
    document.getElementById('btn-snap').style.display    = 'none';
    document.getElementById('btn-analyse').style.display = 'block';
    document.getElementById('btn-retake').style.display  = 'block';
    toast('Photo taken — tap Analyse!');
  }, 'image/jpeg', 0.92);
}

function retake(){
  snapBlob = null;
  document.getElementById('snap-preview').style.display  = 'none';
  document.getElementById('btn-analyse').style.display   = 'none';
  document.getElementById('btn-retake').style.display    = 'none';
  document.getElementById('result-wrap').classList.remove('show');
  document.getElementById('flag-wrap').classList.remove('show');
  startCam();
}

function analyseSnap(){
  if(!snapBlob){ toast('Take a photo first','e'); return; }
  const btn = document.getElementById('btn-analyse');
  btn.innerHTML = '<span class="spinner"></span>Analysing...';
  btn.disabled = true;

  // Run analysis client-side using canvas — no server needed
  const img = new Image();
  img.onload = () => {
    try {
      const can = document.createElement('canvas');
      const w = img.naturalWidth, h = img.naturalHeight;
      can.width = w; can.height = h;
      const ctx = can.getContext('2d');
      ctx.drawImage(img, 0, 0);

      // Crop centre ROI (where teeth appear)
      const mx = Math.floor(w*0.15), my = Math.floor(h*0.25);
      const rw = w - 2*mx, rh = h - 2*my;
      const roi = ctx.getImageData(mx, my, rw, rh);
      const px = roi.data;

      // Overall luminance & yellowness
      let rSum=0,gSum=0,bSum=0, n=px.length/4;
      for(let i=0;i<px.length;i+=4){ rSum+=px[i]; gSum+=px[i+1]; bSum+=px[i+2]; }
      const rM=rSum/n, gM=gSum/n, bM=bSum/n;
      const L = 0.299*rM + 0.587*gM + 0.114*bM;
      const yellow = (rM+gM)/2 - bM;

      // Edge detection (simple Sobel-like on luminance)
      let edgeSum=0, edgeN=0;
      for(let y=1;y<rh-1;y++){
        for(let x=1;x<rw-1;x++){
          const idx=(y*rw+x)*4;
          const lum=(v)=>0.299*px[v]+0.587*px[v+1]+0.114*px[v+2];
          const gx = lum((y*rw+x+1)*4)-lum((y*rw+x-1)*4);
          const gy = lum(((y+1)*rw+x)*4)-lum(((y-1)*rw+x)*4);
          edgeSum += Math.sqrt(gx*gx+gy*gy);
          edgeN++;
        }
      }
      const edgeMean = edgeSum/edgeN;
      const edgeLabel = edgeMean>18?'Sharp':edgeMean>9?'Moderate':'Soft';

      // Overall grade
      const grade = L>155?'Excellent':L>100?'Good':L>50?'Fair':'Stained';
      const gradeColor = {Excellent:'#00e676',Good:'#00d4b8',Fair:'#f59e0b',Stained:'#ef4444'}[grade];

      // Per-tooth columns (8 segments)
      const tw = Math.max(1, Math.floor(rw/8));
      const detected = [];
      for(let i=0;i<8;i++){
        const x1=i*tw, x2=Math.min((i+1)*tw,rw);
        let pr=0,pg=0,pb=0,pn=0;
        for(let y=0;y<rh;y++){
          for(let x=x1;x<x2;x++){
            const idx=(y*rw+x)*4;
            pr+=px[idx]; pg+=px[idx+1]; pb+=px[idx+2]; pn++;
          }
        }
        const pR=pr/pn, pG=pg/pn, pB=pb/pn;
        const pL=0.299*pR+0.587*pG+0.114*pB;
        if(pL<30) continue;
        const pY=(pR+pG)/2-pB;
        const pg2=pY>40?'Stained':pL>155?'Excellent':pL>100?'Good':'Fair';
        const conf=Math.min(0.99,Math.max(0.40,pL/255*1.3));
        detected.push({tooth:i+1,conf:Math.round(conf*100)/100,grade:pg2,L:Math.round(pL*10)/10});
      }

      const flags=[];
      if(detected.length===0) flags.push('No_Teeth_Detected');
      else if(detected.length<4) flags.push('Few_Teeth_Visible — open mouth wider');
      if(yellow>45) flags.push('Staining_Detected — whitening recommended');

      const gmap={Excellent:'#00e676',Good:'#00d4b8',Fair:'#f59e0b',Stained:'#ef4444'};
      const results=[{
        label:`Overall: ${grade}`,conf:Math.round(L/255*100)/100,
        grade,color:gradeColor,edge:edgeLabel,
        tooth_count:detected.length,
        luminance:Math.round(L*10)/10,
        yellowness:Math.round(yellow*10)/10,
        is_summary:true
      },...detected.map(d=>({label:`Tooth ${d.tooth}`,conf:d.conf,grade:d.grade,color:gmap[d.grade]||'#aaa'}))];

      showResults(results, flags);
      const sc=parseInt(document.getElementById('ss').textContent||'0');
      document.getElementById('ss').textContent=sc+1;
    } catch(e){ toast('Analysis error: '+e.message,'e'); }
    btn.innerHTML='🔍 Analyse with AI'; btn.disabled=false;
  };
  img.onerror = () => { toast('Could not load image','e'); btn.innerHTML='🔍 Analyse with AI'; btn.disabled=false; };
  img.src = URL.createObjectURL(snapBlob);
}

function showResults(results, flags){
  // flags
  const fw = document.getElementById('flag-wrap');
  if(flags && flags.length){
    fw.innerHTML = flags.map(f=>`<div class="flag-item">⚠ ${f}</div>`).join('');
    fw.classList.add('show');
  } else {
    fw.classList.remove('show');
  }

  // summary row (first result with is_summary)
  const summary = results.find(r=>r.is_summary) || results[0];
  if(summary){
    lastScanSummary = `${summary.label} · Edge: ${summary.edge||'—'} · Teeth: ${summary.tooth_count||'—'}`;
    document.getElementById('r-summary').innerHTML = `
      <div class="r-sum-row">
        <span class="r-label">Overall Grade</span>
        <span class="r-grade" style="color:${summary.color}">${summary.grade}</span>
      </div>
      <div class="r-sum-row">
        <span class="r-label">Brightness (L)</span>
        <span class="r-val">${summary.luminance||'—'}</span>
      </div>
      <div class="r-sum-row">
        <span class="r-label">Edge Detail</span>
        <span class="r-val" style="color:var(--teal)">${summary.edge||'—'}</span>
      </div>
      <div class="r-sum-row">
        <span class="r-label">Yellowness</span>
        <span class="r-val" style="color:${(summary.yellowness||0)>40?'#ef4444':'#00e676'}">${summary.yellowness||'—'}</span>
      </div>
      <div class="r-sum-row">
        <span class="r-label">Teeth Detected</span>
        <span class="r-val">${summary.tooth_count||'—'}</span>
      </div>`;
  }

  // individual teeth grid
  const teeth = results.filter(r=>!r.is_summary);
  document.getElementById('tooth-grid').innerHTML = teeth.map(t=>`
    <div class="tooth-card">
      <span class="tooth-num">${t.label}</span>
      <span class="tooth-g" style="color:${t.color}">${t.grade}</span>
      <span class="tooth-c">${Math.round(t.conf*100)}%</span>
    </div>`).join('');

  document.getElementById('result-wrap').classList.add('show');
}

function goBook(){
  // pre-fill scan result into booking form
  if(lastScanSummary){
    document.getElementById('scan-note').textContent = lastScanSummary;
    document.getElementById('scan-note-wrap').style.display = 'block';
    // auto-select service based on grade
    const sel = document.getElementById('av');
    if(lastScanSummary.includes('Stained')) sel.value='Teeth Whitening';
    else if(lastScanSummary.includes('Fair')) sel.value='Professional Cleaning';
    else sel.value='General Check-up';
  }
  go('appointments');
}

// ── Doctors ──────────────────────────────────────────────────────────────────
function rDocs(){
  document.getElementById('dlist').innerHTML = DOCS.map(d=>`
    <div class="dc" onclick="pickDoc(${d.id},'${d.n}')">
      <div class="doc-avatar">
        <img class="dphoto" src="${d.img}" alt="${d.n}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/>
        <div class="dav" style="background:${d.bg};display:none">${d.e}</div>
      </div>
      <div><div class="dn">${d.n}</div><div class="ds">${d.s}</div><div class="dr">${d.r}</div></div>
      <div style="margin-left:auto;font-size:1.1rem;color:var(--teal)">›</div>
    </div>`).join('');
}
function pickDoc(id,n){
  go('appointments');
  document.getElementById('ad').value = id;
  toast('Booking with '+n);
}

// ── Appointments ─────────────────────────────────────────────────────────────
function gA(){try{return JSON.parse(localStorage.getItem('ls_v3')||'[]')}catch{return[]}}
function sA(a){localStorage.setItem('ls_v3',JSON.stringify(a))}
function uSt(){document.getElementById('sa').textContent=gA().length}

function book(){
  const n   = document.getElementById('an').value.trim();
  const d   = document.getElementById('adate').value;
  const t   = document.getElementById('at').value;
  const v   = document.getElementById('av').value;
  const doc = DOCS[document.getElementById('ad').selectedIndex];
  const note= document.getElementById('scan-note').textContent||'';
  if(!n){toast('Enter your name','e');return}
  if(!d){toast('Pick a date','e');return}
  const a = gA();
  a.unshift({id:Date.now(),n,d,t,v,doc:doc.n,note});
  sA(a); uSt(); lAppts();
  toast('Booked ✓');
  // save to server too
  fetch('/api/book',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name:n,date:d,time:t,service:v,doctor:doc.n,note})
  }).catch(()=>{});
}

function lAppts(){
  const a = gA();
  document.getElementById('alist').innerHTML = a.length
    ? a.map(x=>`
        <div class="item">
          <div>
            <div class="in">${x.n}</div>
            <div class="im">${x.d} ${x.t} · ${x.doc.split(' ').slice(0,2).join(' ')}</div>
            ${x.note?`<div class="im" style="color:var(--teal);font-size:.65rem">${x.note}</div>`:''}
            <span class="bdg">${x.v}</span>
          </div>
          <button class="del" onclick="dA(${x.id})">🗑</button>
        </div>`).join('')
    : '<div style="text-align:center;color:var(--muted);padding:20px;font-size:.82rem">No appointments yet</div>';
}
function dA(id){sA(gA().filter(a=>a.id!==id));lAppts();uSt();}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(m,t){
  const e = document.getElementById('tst');
  e.textContent = m;
  e.style.background = t==='e'?'#ef4444':'var(--teal)';
  e.style.color = t==='e'?'#fff':'#000';
  e.classList.add('show');
  setTimeout(()=>e.classList.remove('show'),3000);
}

uSt();
</script>
</body>
</html>"""

MANIFEST = '{"name":"LuxeSmile Dental","short_name":"LuxeSmile","display":"standalone","background_color":"#07080f","theme_color":"#00d4b8"}'


# ── SQLite ────────────────────────────────────────────────────────────────────
def _db():
    path = os.path.join(os.path.expanduser('~'), 'luxesmile.db')
    conn = sqlite3.connect(path)
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY, name TEXT, date TEXT, time TEXT,
        service TEXT, doctor TEXT, note TEXT)''')
    conn.commit()
    return conn


# ── HTTP handler ──────────────────────────────────────────────────────────────
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = self.path.split('?')[0]
        if p in ('/', '/index.html'):
            body = HTML.encode('utf-8')  # port injected at startup
            self._ok('text/html;charset=utf-8', body)
        elif p.startswith('/assets/'):
            base = os.path.dirname(os.path.abspath(__file__))
            asset_path = os.path.normpath(os.path.join(base, p.lstrip('/').replace('/', os.sep)))
            if asset_path.startswith(base) and os.path.isfile(asset_path):
                with open(asset_path, 'rb') as f:
                    self._ok('image/png', f.read())
            else:
                self.send_response(404); self.end_headers()
        elif p == '/manifest.json':
            self._ok('application/json', MANIFEST.encode())
        elif p == '/health':
            self._ok('application/json', b'{"ok":true}')
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        ct     = self.headers.get('Content-Type', '')

        if self.path == '/api/analyse':
            try:
                import base64
                d = json.loads(body)
                img_bytes = base64.b64decode(d['image'])
                results, flags = analyse_image(img_bytes)
                self._ok('application/json',
                         json.dumps({'results': results, 'flags': flags}).encode())
            except Exception as e:
                self._ok('application/json',
                         json.dumps({'results':[],'flags':[f'Server error: {e}']}).encode())

        elif self.path == '/api/book':
            try:
                d = json.loads(body)
                c = _db()
                c.execute('INSERT INTO bookings(name,date,time,service,doctor,note) VALUES(?,?,?,?,?,?)',
                          (d.get('name',''), d.get('date',''), d.get('time',''),
                           d.get('service',''), d.get('doctor',''), d.get('note','')))
                c.commit(); c.close()
                self._ok('application/json', b'{"ok":true}')
            except Exception as e:
                self._ok('application/json', json.dumps({'error':str(e)}).encode())
        else:
            self.send_response(404); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _parse_image(self, body, content_type):
        """Extract image bytes from multipart/form-data."""
        try:
            # find boundary
            boundary = None
            for part in content_type.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    # strip optional surrounding quotes e.g. boundary="----WebKit..."
                    boundary = part[9:].strip().strip('"').encode()
                    break
            if not boundary:
                return body  # assume raw image

            # split on boundary and find image part
            parts = body.split(b'--' + boundary)
            for part in parts:
                if b'Content-Disposition' in part and b'filename' in part:
                    # support both \r\n\r\n and \n\n header separators
                    sep = b'\r\n\r\n' if b'\r\n\r\n' in part else b'\n\n'
                    if sep in part:
                        img = part.split(sep, 1)[1]
                        # remove only the trailing CRLF before the next boundary
                        if img.endswith(b'\r\n'):
                            img = img[:-2]
                        elif img.endswith(b'\n'):
                            img = img[:-1]
                        return img
        except Exception:
            pass
        return None

    def _ok(self, ct, body):
        self.send_response(200)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


# ── Buildozer spec ────────────────────────────────────────────────────────────
def _write_spec():
    spec = """\
[app]
title           = LuxeSmile Dental
package.name    = luxesmiledental
package.domain  = org.dental
version         = 1.0
source.dir      = .
source.include_exts = py,png,jpg,jpeg,json
requirements    = python3,kivy,android,pillow
android.minapi  = 26
android.api     = 36
android.ndk     = 25b
android.archs   = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
orientation     = portrait
fullscreen      = 0

[buildozer]
log_level = 2
warn_on_root = 1
"""
    sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'buildozer.spec')
    if not os.path.exists(sp):
        open(sp,'w').write(spec)
        print('✓ buildozer.spec created')


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import socket, signal
    print('=' * 45)
    print('  🦷  LuxeSmile Dental')
    print('=' * 45)

    # find a free port starting from 8766
    actual_port = 8766
    for try_port in range(8766, 8780):
        try:
            t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            t.bind(('localhost', try_port))
            t.close()
            actual_port = try_port
            break
        except OSError:
            continue

    # patch HTML with the actual port number
    import re
    _html = HTML.replace('__PORT__', str(actual_port))

    class App(H):
        _html_data = _html
        def do_GET(self):
            p = self.path.split('?')[0]
            if p in ('/', '/index.html'):
                body = App._html_data.encode('utf-8')
                self._ok('text/html;charset=utf-8', body)
            else:
                super().do_GET()

    print(f'\n✓ Starting on port {actual_port}...')
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(('localhost', actual_port), App)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    print(f'✓ Ready!\n')
    print(f'👉 Open Chrome → http://localhost:{actual_port}')
    print(f'   Then: ⋮ → Add to Home Screen\n')

    _write_spec()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nStopped.')
        srv.shutdown()
