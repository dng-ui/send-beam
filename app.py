
from flask import Flask, request, send_from_directory, redirect, send_file, render_template_string, jsonify
import os, zipfile, io, time, uuid, random, string, shutil
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime

try:
    import qrcode
    import base64
    QR_AVAILABLE = True
except ImportError:
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
        except:
            pass
    return data, True

def room_path(code):
    return os.path.join(BASE, code)

def cleanup_rooms():
    now = time.time()
    for code in os.listdir(BASE):
        rp = room_path(code)
        try:
            if now - os.path.getmtime(rp) > 86400:
                shutil.rmtree(rp)
        except: pass

LANDING = """
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SEND BEAM</title><link rel="icon" href="/static/logo.png"><link rel="manifest" href="/static/manifest.json">
<style>body{font-family:Inter,sans-serif;background:#050507;color:#fff;margin:0}.hero{background:linear-gradient(135deg,#00f2ff 0%,#7000ff 100%);padding:50px 20px;text-align:center}.hero h1{font-size:48px;margin:10px 0 0;letter-spacing:4px;font-weight:900}.hero img{width:90px;background:#fff;border-radius:20px;padding:8px}.btn{padding:16px 32px;border-radius:30px;text-decoration:none;font-weight:900;display:inline-block;border:none;cursor:pointer}.btn-white{background:#fff;color:#000}.container{max-width:760px;margin:auto;padding:30px 20px}.card{background:#121216;border:1px solid #222;border-radius:16px;padding:20px;margin-top:20px}input{width:100%;padding:16px;border-radius:12px;border:1px solid #333;background:#0a0a0a;color:#fff;font-size:18px;text-align:center;letter-spacing:4px}</style></head><body>
<div class="hero"><img src="/static/logo.png"><h1>SEND BEAM</h1><p>TRANSFERT BIDIRECTIONNEL ULTRA RAPIDE</p><div style="margin-top:30px"><a href="/create" class="btn btn-white">CREER UN SALON BEAM</a></div></div>
<div class="container"><div class="card"><h3 style="margin:0">Rejoindre un salon</h3><form action="/join" method="post" style="display:flex;gap:10px;margin-top:15px"><input name="code" placeholder="A8K2P9" maxlength="6" required style="flex:1"><button class="btn btn-white">REJOINDRE</button></form></div></div>
</body></html>
"""

ROOM_HTML = """
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Salon {{code}} - SEND BEAM</title><link rel="icon" href="/static/logo.png">
<style>body{font-family:Inter,sans-serif;background:#08080a;color:#fff;margin:0}.top{background:#0f0f12;padding:15px 20px;display:flex;justify-content:space-between}.code{background:#1a1a22;padding:8px 14px;border-radius:20px;font-weight:900;letter-spacing:2px}.hero2{background:linear-gradient(135deg,#00f2ff 0%,#7000ff 100%);padding:25px;text-align:center}.qr{background:#fff;padding:10px;border-radius:16px;display:inline-block}.container{max-width:760px;margin:auto;padding:20px}.file{background:#121216;border:1px solid #222;border-radius:14px;padding:14px;display:flex;gap:12px;margin-bottom:10px}.btn{background:#fff;color:#000;padding:8px 16px;border-radius:20px;text-decoration:none;font-weight:900;font-size:12px}.upload{border:2px dashed #333;border-radius:16px;padding:22px;text-align:center;background:#111116;margin-top:20px}</style></head><body>
<div class="top"><b>SEND BEAM LIVE</b><div class="code">{{code}}</div></div>
<div class="hero2">
{% if is_url %}
<img src="https://api.qrserver.com/v1/create-qr-code/?size=160x160&data={{qr}}" style="background:#fff;padding:10px;border-radius:12px">
{% else %}
<div class="qr"><img src="data:image/png;base64,{{qr}}" width="150"></div>
{% endif %}
<p><b style="background:rgba(0,0,0,.4);padding:6px 14px;border-radius:20px">{{host}}/r/{{code}}</b></p>
</div>
<div class="container">
<div id="files">{{files_html}}</div>
<form class="upload" action="/r/{{code}}/upload" method="post" enctype="multipart/form-data">
<h3>Envoyer vers l'autre</h3>
<input type="file" name="file" multiple required style="color:#fff;margin:12px 0"><br>
<button class="btn" style="border:none;background:#00f2ff;padding:12px 28px">BEAM MAINTENANT</button>
</form>
</div>
<script>setInterval(()=>{fetch('/r/{{code}}/list').then(r=>r.text()).then(h=>{document.getElementById('files').innerHTML=h})}, 3000);</script>
</body></html>
"""

@app.route('/')
def landing(): return LANDING

@app.route('/create')
def create():
    cleanup_rooms()
    code = gen_code()
    while os.path.exists(room_path(code)): code = gen_code()
    os.makedirs(room_path(code), exist_ok=True)
    return redirect(f'/r/{code}')

@app.route('/join', methods=['POST'])
def join():
    code = request.form.get('code','').strip().upper()
    if not os.path.exists(room_path(code)): return f"Salon {code} introuvable <a href='/'>Retour</a>", 404
    return redirect(f'/r/{code}')

def render_files(code):
    rp = room_path(code)
    if not os.path.exists(rp): return "<p>Salon vide</p>"
    items = os.listdir(rp)
    if not items: return "<p style='text-align:center;color:#444'>Aucun fichier encore.</p>"
    html = ""
    for it in sorted(items, key=lambda x: os.path.getmtime(os.path.join(rp,x)), reverse=True):
        fp = os.path.join(rp,it)
        size = os.path.getsize(fp)/1024/1024
        html += f'<div class="file"><b>{it}</b> <span style="color:#777">{size:.2f} MB</span><div style="flex:1"></div><a href="/r/{code}/f/{it}" class="btn">TELECHARGER</a></div>'
    return html

@app.route('/r/<code>')
def room(code):
    code = code.upper()
    if not os.path.exists(room_path(code)): return "Salon introuvable", 404
    host = request.host_url.rstrip('/')
    qr_data, is_url = make_qr(f"{host}/r/{code}")
    files_html = render_files(code)
    return render_template_string(ROOM_HTML, code=code, qr=qr_data, is_url=is_url, host=host, files_html=files_html)

@app.route('/r/<code>/list')
def room_list(code): return render_files(code.upper())

@app.route('/r/<code>/upload', methods=['POST'])
def room_upload(code):
    code = code.upper()
    rp = room_path(code)
    os.makedirs(rp, exist_ok=True)
    for f in request.files.getlist('file'):
        if f.filename:
            name = secure_filename(f.filename)
            f.save(os.path.join(rp, name))
    return redirect(f'/r/{code}')

@app.route('/r/<code>/f/<path:fname>')
def room_dl(code, fname):
    return send_from_directory(room_path(code.upper()), fname, as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
