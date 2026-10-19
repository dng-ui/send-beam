
from flask import Flask, request, send_from_directory, redirect, render_template_string
import os, random, string, shutil, time, zipfile
from werkzeug.utils import secure_filename
from io import BytesIO

try:
    import qrcode, base64
    QR_AVAILABLE = True
except:
    QR_AVAILABLE = False
    base64 = None
    qrcode = None

app = Flask(__name__, static_folder='static')
BASE = "rooms"
os.makedirs(BASE, exist_ok=True)

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def make_qr(data):
    if QR_AVAILABLE:
        try:
            img = qrcode.make(data)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode(), False
        except: pass
    return data, True

def room_path(code): return os.path.join(BASE, code)

def cleanup_rooms():
    now=time.time()
    for code in os.listdir(BASE):
        rp=room_path(code)
        try:
            if now - os.path.getmtime(rp) > 86400: shutil.rmtree(rp)
        except: pass

LANDING = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SEND BEAM</title><link rel="icon" href="/static/logo.png"><link rel="manifest" href="/static/manifest.json"><style>body{font-family:Inter,sans-serif;background:#050507;color:#fff;margin:0}.hero{background:linear-gradient(135deg,#00f2ff 0%,#7000ff 100%);padding:40px 20px;text-align:center}.hero h1{font-size:42px;letter-spacing:4px;font-weight:900;margin:10px 0}.hero img{width:80px;background:#fff;border-radius:16px;padding:6px}.btn{padding:14px 28px;border-radius:30px;text-decoration:none;font-weight:900;display:inline-block;border:none;cursor:pointer}.btn-white{background:#fff;color:#000}.container{max-width:760px;margin:auto;padding:20px}.card{background:#121216;border:1px solid #222;border-radius:16px;padding:20px;margin-top:20px}input{width:100%;padding:14px;border-radius:10px;border:1px solid #333;background:#0a0a0a;color:#fff;font-size:16px;text-align:center;letter-spacing:3px}</style></head><body><div class="hero"><img src="/static/logo.png"><h1>SEND BEAM</h1><p>ENVOIE FICHIERS + DOSSIERS COMPLETS - BIDIRECTIONNEL</p><a href="/create" class="btn btn-white" style="margin-top:20px">CREER UN SALON BEAM</a></div><div class="container"><div class="card"><h3>Rejoindre</h3><form action="/join" method="post" style="display:flex;gap:10px"><input name="code" placeholder="A8K2P9" maxlength="6" required><button class="btn btn-white">REJOINDRE</button></form></div></div></body></html>"""

ROOM_HTML = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Salon {{code}}</title><link rel="icon" href="/static/logo.png"><style>body{font-family:Inter,sans-serif;background:#08080a;color:#fff;margin:0}.top{background:#0f0f12;padding:14px 20px;display:flex;justify-content:space-between;align-items:center}.code{background:#1a1a22;padding:6px 12px;border-radius:20px;font-weight:900}.hero2{background:linear-gradient(135deg,#00f2ff 0%,#7000ff 100%);padding:20px;text-align:center}.qr{background:#fff;padding:8px;border-radius:12px;display:inline-block}.container{max-width:760px;margin:auto;padding:20px}.file{background:#121216;border:1px solid #222;border-radius:12px;padding:12px;display:flex;gap:10px;margin-bottom:8px;align-items:center}.btn{background:#fff;color:#000;padding:6px 12px;border-radius:16px;text-decoration:none;font-weight:800;font-size:12px}.upload{border:2px dashed #333;border-radius:14px;padding:18px;text-align:center;background:#111116;margin-top:16px}.upload-folder{border-color:#00f2ff;background:#0a1a1a} .badge{background:#00f2ff;color:#000;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:900}</style></head><body>
<div class="top"><b>BEAM LIVE {{code}}</b><div class="code">{{code}}</div></div>
<div class="hero2">
{% if is_url %}<img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={{qr}}" style="background:#fff;padding:8px;border-radius:10px">{% else %}<div class="qr"><img src="data:image/png;base64,{{qr}}" width="130"></div>{% endif %}
<p style="margin-top:10px"><b style="background:rgba(0,0,0,.4);padding:4px 12px;border-radius:20px;font-size:12px">{{host}}/r/{{code}}</b></p>
</div>
<div class="container">
<div id="files">{{files_html}}</div>
<form class="upload" action="/r/{{code}}/upload" method="post" enctype="multipart/form-data">
<h3 style="margin:0">📄 Envoyer FICHIER(S)</h3><p style="color:#666;font-size:11px">Plusieurs fichiers possibles</p>
<input type="file" name="file" multiple required style="margin:10px 0"><br>
<button class="btn" style="background:#fff">BEAM FICHIERS</button>
</form>
<form class="upload upload-folder" action="/r/{{code}}/upload_folder" method="post" enctype="multipart/form-data">
<h3 style="margin:0">📁 Envoyer DOSSIER COMPLET <span class="badge">NOUVEAU</span></h3><p style="color:#00f2ff;font-size:11px">Ton dossier Smadav avec tous ses sous-dossiers sera zippé auto</p>
<input type="file" name="folder" webkitdirectory directory multiple required style="margin:10px 0"><br>
<button class="btn" style="background:#00f2ff">📁 BEAM DOSSIER</button>
</form>
</div>
<script>setInterval(()=>{fetch('/r/{{code}}/list').then(r=>r.text()).then(h=>{document.getElementById('files').innerHTML=h})}, 3000);</script>
</body></html>"""

@app.route('/')
def landing(): return LANDING

@app.route('/create')
def create():
    cleanup_rooms()
    code=gen_code()
    while os.path.exists(room_path(code)): code=gen_code()
    os.makedirs(room_path(code), exist_ok=True)
    return redirect(f'/r/{code}')

@app.route('/join', methods=['POST'])
def join():
    code=request.form.get('code','').strip().upper()
    if not os.path.exists(room_path(code)): return "Salon introuvable",404
    return redirect(f'/r/{code}')

def render_files(code):
    rp=room_path(code)
    if not os.path.exists(rp): return "<p>Salon vide</p>"
    items=os.listdir(rp)
    if not items: return "<p style='text-align:center;color:#555'>Aucun fichier. Envoie ton dossier Smadav !</p>"
    html=""
    for it in sorted(items, key=lambda x: os.path.getmtime(os.path.join(rp,x)), reverse=True):
        fp=os.path.join(rp,it)
        size=os.path.getsize(fp)/1024/1024
        icon="📁" if it.endswith('.zip') else "📄"
        html+=f'<div class="file"><div style="font-size:22px">{icon}</div><div><b>{it}</b><br><span style="color:#777;font-size:11px">{size:.2f} MB</span></div><div style="flex:1"></div><a href="/r/{code}/f/{it}" class="btn">TELECHARGER</a></div>'
    return html

@app.route('/r/<code>')
def room(code):
    code=code.upper()
    if not os.path.exists(room_path(code)): return "Salon introuvable",404
    host=request.host_url.rstrip('/')
    qr_data,is_url=make_qr(f"{host}/r/{code}")
    return render_template_string(ROOM_HTML, code=code, qr=qr_data, is_url=is_url, host=host, files_html=render_files(code))

@app.route('/r/<code>/list')
def room_list(code): return render_files(code.upper())

@app.route('/r/<code>/upload', methods=['POST'])
def upload_files(code):
    code=code.upper()
    rp=room_path(code)
    os.makedirs(rp, exist_ok=True)
    for f in request.files.getlist('file'):
        if f.filename:
            name=secure_filename(f.filename)
            f.save(os.path.join(rp,name))
    return redirect(f'/r/{code}')

@app.route('/r/<code>/upload_folder', methods=['POST'])
def upload_folder(code):
    code=code.upper()
    rp=room_path(code)
    os.makedirs(rp, exist_ok=True)
    files=request.files.getlist('folder')
    if not files: return redirect(f'/r/{code}')
    first_path = files[0].filename
    root_folder = first_path.split('/')[0] if '/' in first_path else "dossier"
    zip_name = f"{secure_filename(root_folder)}-dossier.zip"
    zip_path = os.path.join(rp, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            data = f.read()
            zf.writestr(f.filename, data)
    return redirect(f'/r/{code}')

@app.route('/r/<code>/f/<path:fname>')
def dl(code,fname):
    return send_from_directory(room_path(code.upper()), fname, as_attachment=True)

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
