"""
Diplomacia Auto Perk Bot - API Mode
بيكلم API الموقع مباشرة بدون browser
HTML مدمج بدون templates
"""
import os, json, time, threading, logging, requests
from datetime import datetime
from flask import Flask, jsonify, request, Response
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'diplo-bot-2024')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

BASE_URL = "https://diplomacia.com.tr/api"
PERKS = {
    'barracks':       {'label': 'BARRACKS',        'key': 'barracks'},
    'war_techniques': {'label': 'WAR TECHNIQUES',  'key': 'war_techniques'},
    'scientist':      {'label': 'SCIENTIST',        'key': 'bilim_insani'},
}

# ── HTML مدمج ──────────────────────────────────────
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Diplomacia Bot</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js"></script>
<style>
:root{--gold:#c8a84b;--bg:#07071a;--card:#0f0f28;--panel:#161635;--border:rgba(200,168,75,.18);--green:#4caf72;--red:#e94560;--blue:#4a9eff;--text:#d0d0e8;--muted:#505078}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
header{background:rgba(7,7,26,.97);border-bottom:1px solid var(--border);padding:0 1.2rem;height:54px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.logo{color:var(--gold);font-weight:700;font-size:1rem;letter-spacing:2px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;margin-left:6px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.main{max-width:900px;margin:0 auto;padding:1.2rem;padding-bottom:80px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.2rem}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;transition:border-color .2s}
.card.running{border-color:rgba(76,175,114,.4)}
.card.error{border-color:rgba(233,69,96,.4)}
.ch{background:var(--panel);padding:.9rem 1rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.av{width:36px;height:36px;border-radius:50%;background:#1a1a40;border:1.5px solid var(--gold);display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}
.cn{font-weight:700;font-size:13px;color:var(--gold)}
.cs{font-size:10px;color:var(--muted);margin-top:2px}
.badge{margin-right:auto;padding:2px 9px;border-radius:20px;font-size:10px;font-weight:700}
.b-run{background:rgba(76,175,114,.15);color:var(--green);border:1px solid rgba(76,175,114,.3)}
.b-stop{background:rgba(80,80,120,.2);color:var(--muted);border:1px solid var(--border)}
.b-err{background:rgba(233,69,96,.12);color:var(--red);border:1px solid rgba(233,69,96,.3)}
.cb{padding:.9rem 1rem}
.res{display:flex;gap:8px;margin-bottom:.8rem}
.rc{flex:1;background:var(--panel);border-radius:6px;padding:5px 8px;font-size:11px}
.rc span{color:var(--gold);font-weight:700}
.xb{height:3px;background:var(--panel);border-radius:2px;margin-bottom:.8rem;overflow:hidden}
.xf{height:100%;background:var(--gold);border-radius:2px;transition:width 1s}
.slbl{font-size:10px;color:var(--muted);letter-spacing:1.5px;margin-bottom:5px}
.prks{display:flex;flex-direction:column;gap:5px;margin-bottom:.8rem}
.pr{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;background:var(--panel);cursor:pointer;border:1px solid transparent;transition:all .15s}
.pr:hover{background:#1e1e45}
.pr.sel{border-color:rgba(200,168,75,.4);background:rgba(200,168,75,.07)}
.pi{width:24px;height:24px;border-radius:5px;background:rgba(200,168,75,.1);display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0}
.pn{font-size:11px;font-weight:600}
.pd{font-size:10px;color:var(--muted)}
.pl{margin-right:auto;font-size:10px;color:var(--gold);background:rgba(200,168,75,.1);padding:2px 7px;border-radius:4px}
.pcd{font-size:10px;color:var(--muted);min-width:40px;text-align:center}
.pcd.rdy{color:var(--green);font-weight:700}
.pcd.upg{color:var(--blue)}
.cur{display:flex;gap:6px;margin-bottom:.8rem}
.cb2{flex:1;padding:5px;border:1px solid var(--border);border-radius:6px;background:transparent;color:var(--muted);font-size:11px;cursor:pointer;transition:all .15s;text-align:center}
.cb2.act{border-color:var(--gold);color:var(--gold);background:rgba(200,168,75,.1)}
.cd-big{text-align:center;font-size:2rem;font-weight:700;color:var(--green);letter-spacing:3px;margin:.5rem 0;min-height:48px}
.cd-big.wait{color:var(--gold)}
.ctrl{display:flex;gap:7px;padding:.8rem 1rem;border-top:1px solid var(--border)}
.btn{flex:1;padding:8px;border:1px solid var(--border);border-radius:7px;background:transparent;color:var(--text);font-size:12px;font-weight:700;cursor:pointer;transition:all .15s;display:flex;align-items:center;justify-content:center;gap:5px}
.btn:hover{background:#1e1e45}
.btn-s{background:rgba(76,175,114,.12);border-color:rgba(76,175,114,.4);color:var(--green)}
.btn-s:hover{background:rgba(76,175,114,.22)}
.btn-x{background:rgba(233,69,96,.1);border-color:rgba(233,69,96,.35);color:var(--red)}
.btn-x:hover{background:rgba(233,69,96,.2)}
.btn-g{background:rgba(200,168,75,.1);border-color:rgba(200,168,75,.4);color:var(--gold)}
.inp{width:100%;padding:8px 10px;background:var(--panel);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;outline:none;transition:border-color .15s;margin-bottom:7px}
.inp:focus{border-color:var(--gold)}
.log-panel{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:1rem}
.lh{display:flex;align-items:center;justify-content:space-between;padding:.7rem 1rem;border-bottom:1px solid var(--border);background:var(--panel)}
.lt{font-size:.7rem;color:rgba(200,168,75,.7);letter-spacing:2px}
.lb{background:none;border:none;color:var(--muted);font-size:11px;cursor:pointer}
.lb:hover{color:var(--red)}
.log-body{padding:.7rem 1rem;max-height:200px;overflow-y:auto;font-family:monospace;font-size:11px;line-height:1.9}
.ll{display:flex;gap:8px}
.lt2{color:var(--muted);flex-shrink:0}
.la{color:rgba(200,168,75,.6);flex-shrink:0;min-width:75px}
.lm{color:var(--text)}
.ll.ok .lm{color:var(--green)}
.ll.warn .lm{color:var(--gold)}
.ll.error .lm{color:var(--red)}
.ll.info .lm{color:var(--blue)}
.tok-section{padding:.8rem 1rem;border-top:1px solid var(--border)}
.bnav{position:fixed;bottom:0;left:0;right:0;background:rgba(7,7,26,.98);border-top:1px solid var(--border);display:flex}
.ni{flex:1;display:flex;flex-direction:column;align-items:center;padding:8px 0;gap:3px;font-size:9px;letter-spacing:1px;color:var(--muted);cursor:pointer;border:none;background:none;color:var(--muted);font-family:inherit;transition:color .15s}
.ni.act{color:var(--gold)}
.ni-icon{font-size:18px}
.page{display:none}
.page.act{display:block}
/* Token status indicator */
.tok-status{font-size:11px;padding:4px 8px;border-radius:4px;margin-bottom:8px;display:none}
.tok-status.ok{background:rgba(76,175,114,.15);color:var(--green);display:block}
.tok-status.err{background:rgba(233,69,96,.12);color:var(--red);display:block}
@media(max-width:600px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div class="logo">⚔ DIPLOMACIA BOT</div>
  <div><span class="dot"></span><span id="hstatus" style="font-size:11px;color:var(--muted)">جاري الاتصال...</span></div>
</header>

<div class="main">

<!-- PAGE: HOME -->
<div id="page-home" class="page act">
  <div class="grid" id="acc-grid"></div>

  <div style="font-size:.7rem;color:rgba(200,168,75,.6);letter-spacing:2px;margin-bottom:.7rem">السجل</div>
  <div class="log-panel">
    <div class="lh"><span class="lt">ACTIVITY LOG</span><button class="lb" onclick="clearLog()">مسح</button></div>
    <div class="log-body" id="log-body">
      <div class="ll info"><span class="lt2">--:--</span><span class="la">[SYSTEM]</span><span class="lm">البوت جاهز</span></div>
    </div>
  </div>
</div>

<!-- PAGE: SETTINGS -->
<div id="page-settings" class="page">
  <div style="font-size:.7rem;color:rgba(200,168,75,.6);letter-spacing:2px;margin-bottom:.7rem">إضافة / تحديث Token</div>
  <div class="log-panel">
    <div style="padding:.9rem 1rem">
      <div style="font-size:12px;color:var(--muted);margin-bottom:.7rem">حساب 1</div>
      <div class="tok-status" id="ts1"></div>
      <input class="inp" id="tok1-name" placeholder="اسم الحساب (اختياري)">
      <input class="inp" id="tok1" placeholder="Token الحساب الأول (eyJhbG...)">
      <button class="btn btn-g" style="width:100%;margin-bottom:1rem" onclick="saveToken('1')">💾 حفظ الحساب 1</button>

      <div style="font-size:12px;color:var(--muted);margin-bottom:.7rem">حساب 2</div>
      <div class="tok-status" id="ts2"></div>
      <input class="inp" id="tok2-name" placeholder="اسم الحساب (اختياري)">
      <input class="inp" id="tok2" placeholder="Token الحساب الثاني (eyJhbG...)">
      <button class="btn btn-g" style="width:100%;margin-bottom:1rem" onclick="saveToken('2')">💾 حفظ الحساب 2</button>
    </div>
  </div>

  <div style="font-size:.7rem;color:rgba(200,168,75,.6);letter-spacing:2px;margin-bottom:.7rem">كيف تجيب الـ Token؟</div>
  <div class="log-panel">
    <div style="padding:.9rem 1rem;font-size:12px;line-height:2.2;color:var(--muted)">
      <div>1️⃣ افتح diplomacia.com.tr في المتصفح</div>
      <div>2️⃣ اضغط F12 ← Network ← XHR/Fetch</div>
      <div>3️⃣ اعمل أي action في اللعبة</div>
      <div>4️⃣ افتح أي request وابحث عن <b style="color:var(--gold)">Authorization: Bearer eyJ...</b></div>
      <div>5️⃣ انسخ الـ token من بعد كلمة Bearer</div>
      <hr style="border-color:var(--border);margin:.5rem 0">
      <div>⏱ Token بيخلص بعد ~7 أيام — جدده من هنا</div>
      <div>🔒 Token محفوظ في memory السيرفر (مش في الـ DB)</div>
      <div>🔄 البوت بيحاول كل دقيقة لو في مشكلة</div>
    </div>
  </div>
</div>

</div><!-- /main -->

<nav class="bnav">
  <button class="ni act" id="nav-home" onclick="switchPage('home',this)">
    <span class="ni-icon">⚔</span>الرئيسية
  </button>
  <button class="ni" id="nav-settings" onclick="switchPage('settings',this)">
    <span class="ni-icon">⚙</span>الإعدادات
  </button>
</nav>

<script>
const PERKS = {
  barracks:       {label:'BARRACKS',       icon:'🏰', desc:'+Military Power'},
  war_techniques: {label:'WAR TECHNIQUES', icon:'⚔',  desc:'+War Damage'},
  scientist:      {label:'SCIENTIST',      icon:'🔬', desc:'+Factory Income'},
};

const socket = io();
let state = {};

socket.on('connect', () => {
  document.getElementById('hstatus').textContent = 'متصل بالسيرفر';
});
socket.on('disconnect', () => {
  document.getElementById('hstatus').textContent = 'انقطع الاتصال!';
});
socket.on('update', s => { state = s; renderAll(); });
socket.on('log', entry => addLogEntry(entry));

function renderAll() {
  const grid = document.getElementById('acc-grid');
  grid.innerHTML = ['1','2'].map(id => renderCard(id, state[id])).join('');
  let active = Object.values(state).filter(a => a.enabled).length;
  document.getElementById('hstatus').textContent = active + ' حساب نشط';
}

function renderCard(id, acc) {
  if (!acc) return '';
  const xpPct = acc.xp_pct || 0;
  const stClass = acc.status === 'running' ? 'running' : acc.status === 'error' ? 'error' : '';
  const badge = acc.enabled
    ? `<span class="badge b-run">نشط</span>`
    : acc.status === 'error'
    ? `<span class="badge b-err">خطأ</span>`
    : `<span class="badge b-stop">موقف</span>`;

  const perksHtml = Object.entries(PERKS).map(([key, p]) => {
    const isSel = acc.perk === key;
    const lvl = acc.level?.[key] || '?';
    let cdHtml = `<span class="pcd rdy">جاهز ✓</span>`;
    if (isSel && acc.enabled && acc.cooldown > 0) {
      cdHtml = `<span class="pcd upg">${fmt(acc.cooldown)}</span>`;
    }
    return `<div class="pr ${isSel?'sel':''}" onclick="selPerk('${id}','${key}')">
      <div class="pi">${p.icon}</div>
      <div><div class="pn">${p.label}</div><div class="pd">${p.desc}</div></div>
      <div class="pl">Lv.${lvl}</div>${cdHtml}</div>`;
  }).join('');

  const cdText = acc.enabled && acc.cooldown > 0
    ? `<div class="cd-big wait">${fmtCd(acc.cooldown)}</div>`
    : acc.enabled
    ? `<div class="cd-big">⚡ جاهز</div>`
    : `<div class="cd-big" style="font-size:1rem;color:var(--muted)">موقف</div>`;

  const hasToken = acc.token ? '✅' : '❌';
  const lvlText = acc.level_num !== '?' ? `Lv.${acc.level_num}` : '';

  return `<div class="card ${stClass}" id="card-${id}">
    <div class="ch">
      <div class="av">🎮</div>
      <div>
        <div class="cn">${acc.name} ${hasToken} <span style="font-size:10px;color:var(--muted)">${lvlText}</span></div>
        <div class="cs">ترقيات: ${acc.upgrades} | آخر: ${acc.last_upgrade}</div>
      </div>
      ${badge}
    </div>
    <div class="cb">
      <div class="res">
        <div class="rc">💵 <span>${acc.balance}</span></div>
        <div class="rc">💎 <span>${acc.diamonds}</span></div>
        <div class="rc" title="XP Progress">🔰 <span>${xpPct}%</span></div>
      </div>
      <div class="xb"><div class="xf" style="width:${xpPct}%"></div></div>
      <div class="slbl">العملة</div>
      <div class="cur">
        <button class="cb2 ${acc.currency==='money'?'act':''}" onclick="selCur('${id}','money')">💵 Money</button>
        <button class="cb2 ${acc.currency==='diamond'?'act':''}" onclick="selCur('${id}','diamond')">💎 Diamond</button>
      </div>
      <div class="slbl">اختر البيرك</div>
      <div class="prks">${perksHtml}</div>
      ${cdText}
    </div>
    <div class="ctrl">
      ${acc.enabled
        ? `<button class="btn btn-x" onclick="stopAcc('${id}')">⏹ إيقاف</button>`
        : `<button class="btn btn-s" onclick="startAcc('${id}')">▶ تشغيل</button>`}
      <button class="btn" onclick="switchPage('settings',document.getElementById('nav-settings'))">🔑 Token</button>
      <button class="btn" onclick="refreshAcc('${id}')">🔄</button>
    </div>
  </div>`;
}

// ── Actions ──────────────────────────────────────
async function startAcc(id) {
  const r = await fetch(`/api/start/${id}`, {method:'POST'});
  const d = await r.json();
  if (d.error) alert(d.error);
}
async function stopAcc(id) {
  await fetch(`/api/stop/${id}`, {method:'POST'});
}
async function selPerk(id, perk) {
  await fetch(`/api/config/${id}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({perk})
  });
}
async function selCur(id, currency) {
  await fetch(`/api/config/${id}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({currency})
  });
}
async function saveToken(id) {
  const tok = document.getElementById(`tok${id}`).value.trim();
  const name = document.getElementById(`tok${id}-name`).value.trim();
  if (!tok) { alert('الصق الـ Token أولاً'); return; }
  const r = await fetch(`/api/config/${id}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({token: tok, name: name || undefined})
  });
  const el = document.getElementById(`ts${id}`);
  if (r.ok) {
    el.textContent = '✅ تم حفظ الـ Token بنجاح';
    el.className = 'tok-status ok';
    document.getElementById(`tok${id}`).value = '';
    setTimeout(() => el.className = 'tok-status', 3000);
  } else {
    el.textContent = '❌ خطأ في الحفظ';
    el.className = 'tok-status err';
  }
}
async function refreshAcc(id) {
  await fetch(`/api/refresh/${id}`, {method:'POST'});
}

// ── Log ──────────────────────────────────────────
function addLogEntry(e) {
  const body = document.getElementById('log-body');
  const div = document.createElement('div');
  div.className = `ll ${e.level}`;
  div.innerHTML = `<span class="lt2">${e.time}</span><span class="la">[${state[e.acc_id]?.name || e.acc_id}]</span><span class="lm">${e.msg}</span>`;
  body.insertBefore(div, body.firstChild);
  if (body.children.length > 80) body.lastChild.remove();
}
function clearLog() { document.getElementById('log-body').innerHTML = ''; }

// ── Nav ──────────────────────────────────────────
function switchPage(name, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('act'));
  document.getElementById('page-' + name).classList.add('act');
  document.querySelectorAll('.ni').forEach(n => n.classList.remove('act'));
  btn.classList.add('act');
}

// ── Helpers ───────────────────────────────────────
function fmt(s) {
  s = Math.floor(s);
  if (s < 60) return s + 's';
  if (s < 3600) return Math.floor(s/60) + 'm ' + String(s%60).padStart(2,'0') + 's';
  return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
}
function fmtCd(s) {
  s = Math.floor(s);
  const m = Math.floor(s/60), sc = s%60;
  return `${String(m).padStart(2,'0')}:${String(sc).padStart(2,'0')}`;
}

// ── Init ─────────────────────────────────────────
fetch('/api/state').then(r=>r.json()).then(s => { state = s; renderAll(); });
setInterval(() => {
  Object.keys(state).forEach(id => {
    if (state[id].enabled && state[id].cooldown > 0) {
      state[id].cooldown = Math.max(0, state[id].cooldown - 1);
    }
  });
  renderAll();
}, 1000);
</script>
</body>
</html>"""

# ── State ──────────────────────────────────────────
accounts = {
    '1': {
        'id': '1', 'name': 'Cazirns', 'token': os.environ.get('TOKEN_1', ''),
        'enabled': False, 'status': 'stopped',
        'perk': 'scientist', 'currency': 'diamond',
        'cooldown': 0, 'upgrades': 0, 'last_upgrade': '—',
        'balance': '—', 'diamonds': '—',
        'level': {'barracks': '?', 'war_techniques': '?', 'scientist': '?'},
        'level_num': '?', 'avatar': '', 'flag': '',
        'xp_pct': 0, 'logs': []
    },
    '2': {
        'id': '2', 'name': os.environ.get('NAME_2', 'Hesap 2'), 'token': os.environ.get('TOKEN_2', ''),
        'enabled': False, 'status': 'stopped',
        'perk': 'scientist', 'currency': 'diamond',
        'cooldown': 0, 'upgrades': 0, 'last_upgrade': '—',
        'balance': '—', 'diamonds': '—',
        'level': {'barracks': '?', 'war_techniques': '?', 'scientist': '?'},
        'level_num': '?', 'avatar': '', 'flag': '',
        'xp_pct': 0, 'logs': []
    }
}

# override name for acc1 if env set
if os.environ.get('NAME_1'):
    accounts['1']['name'] = os.environ.get('NAME_1')

stop_events = {}
bot_threads = {}

# ── Logging ────────────────────────────────────────
def add_log(acc_id, msg, level='info'):
    ts = datetime.now().strftime('%H:%M:%S')
    entry = {'time': ts, 'msg': msg, 'level': level}
    accounts[acc_id]['logs'].insert(0, entry)
    accounts[acc_id]['logs'] = accounts[acc_id]['logs'][:60]
    log.info(f"[Acc {acc_id}] {msg}")
    socketio.emit('log', {'acc_id': acc_id, **entry})
    socketio.emit('update', get_state())

# ── API Helpers ────────────────────────────────────
def make_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0',
        'Origin': 'https://diplomacia.com.tr',
        'Referer': 'https://diplomacia.com.tr/',
    }

def api_get(token, path):
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=make_headers(token), timeout=15)
        if r.status_code == 200:
            return r.json()
        log.warning(f"GET {path} → {r.status_code}")
        return None
    except Exception as e:
        log.error(f"GET {path} error: {e}")
        return None

def api_post(token, path, data=None):
    try:
        r = requests.post(f"{BASE_URL}{path}", headers=make_headers(token),
                          json=data or {}, timeout=15)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        log.error(f"POST {path} error: {e}")
        return 0, {}

# ── Refresh Profile ────────────────────────────────
def refresh_profile(acc_id):
    acc = accounts[acc_id]
    if not acc['token']:
        return False
    data = api_get(acc['token'], '/players/profile')
    if not data:
        return False
    try:
        player = data.get('player', data)
        acc['balance']  = f"${player.get('balance', 0):,}"
        acc['diamonds'] = str(player.get('diamonds', 0))
        acc['name']     = player.get('username', acc['name'])
        acc['avatar']   = player.get('avatar_url', '')
        acc['flag']     = player.get('country_flag', '')

        lp = player.get('levelProgress', {})
        pct = lp.get('percentage', 0)
        acc['xp_pct'] = round(pct * 100) if isinstance(pct, float) and pct <= 1 else round(pct)
        acc['level_num'] = player.get('level', '?')

        skills = player.get('skills', {})
        acc['level']['barracks']       = skills.get('kisla', '?')
        acc['level']['war_techniques'] = skills.get('savas_teknikleri', '?')
        acc['level']['scientist']      = skills.get('bilim_insani', '?')

        socketio.emit('update', get_state())
        return True
    except Exception as e:
        log.error(f"Profile parse error acc{acc_id}: {e}")
        return False

# ── Read Cooldown ──────────────────────────────────
def get_cooldown(acc_id):
    acc = accounts[acc_id]
    perk_key = PERKS[acc['perk']]['key']

    # endpoint مخصص للـ skill
    data = api_get(acc['token'], f'/skills/{perk_key}')
    if data:
        try:
            cd = data.get('cooldown_remaining') or data.get('remaining_seconds') or data.get('cooldown', 0)
            if cd and int(cd) > 0:
                return int(cd)
            end_time = data.get('upgrade_end_time') or data.get('upgrading_until')
            if end_time:
                remaining = int(end_time) - int(time.time())
                return max(0, remaining)
            if data.get('is_upgrading') or data.get('upgrading', False):
                return 60
            return 0
        except Exception as e:
            log.error(f"Cooldown parse error: {e}")

    # fallback: profile
    data = api_get(acc['token'], '/players/profile')
    if not data:
        return None
    try:
        player = data.get('player', data)
        skills = player.get('skills', {})
        skill = skills.get(perk_key)
        if isinstance(skill, (int, float)):
            return 0
        if isinstance(skill, dict):
            cd = skill.get('cooldown_remaining', 0) or skill.get('remaining_seconds', 0)
            if cd and int(cd) > 0:
                return int(cd)
        return 0
    except Exception as e:
        log.error(f"Cooldown fallback error: {e}")
        return 0

# ── Do Upgrade ─────────────────────────────────────
def do_upgrade(acc_id):
    acc = accounts[acc_id]
    perk_key = PERKS[acc['perk']]['key']
    currency = 'money' if acc['currency'] == 'money' else 'diamond'

    endpoints_payloads = [
        (f'/skills/{perk_key}/upgrade',         {'currency': currency}),
        (f'/players/skills/upgrade',             {'skill': perk_key, 'currency': currency}),
        (f'/skills/upgrade',                     {'skill': perk_key, 'currency': currency}),
        (f'/players/skills/{perk_key}/upgrade',  {'currency': currency}),
    ]

    for ep, payload in endpoints_payloads:
        status, resp = api_post(acc['token'], ep, payload)
        log.info(f"Upgrade attempt {ep}: status={status} resp={str(resp)[:100]}")
        if status in (200, 201):
            return True, resp
        if status == 400:
            msg = resp.get('message', '') if isinstance(resp, dict) else str(resp)
            if any(w in msg.lower() for w in ['cooldown', 'wait', 'bekle', 'süre']):
                return False, msg
        if status == 401:
            return False, 'Token منتهي الصلاحية'
        if status == 404:
            continue
    return False, 'all endpoints failed'

# ── Bot Loop ───────────────────────────────────────
def bot_loop(acc_id, stop_ev):
    acc = accounts[acc_id]
    add_log(acc_id, f"▶ البوت شغّال — {PERKS[acc['perk']]['label']}", 'ok')
    acc['status'] = 'running'

    if not acc['token']:
        add_log(acc_id, '❌ مفيش Token! أضف Token من الإعدادات', 'error')
        acc['status'] = 'error'
        acc['enabled'] = False
        socketio.emit('update', get_state())
        return

    if refresh_profile(acc_id):
        add_log(acc_id, f"✅ متصل — {acc['name']} | {acc['balance']} | 💎{acc['diamonds']}", 'ok')
    else:
        add_log(acc_id, '⚠️ Token منتهي أو خاطئ — تحقق من الإعدادات', 'warn')
        acc['status'] = 'error'
        acc['enabled'] = False
        socketio.emit('update', get_state())
        return

    fail_count = 0
    MAX_FAILS = 5

    while not stop_ev.is_set():
        try:
            cd = get_cooldown(acc_id)

            if cd is None:
                add_log(acc_id, '⚠️ مش قادر يقرأ الحالة', 'warn')
                acc['cooldown'] = 0
                fail_count += 1
                if fail_count >= MAX_FAILS:
                    add_log(acc_id, f'❌ فشل {MAX_FAILS} مرات متتالية — توقف', 'error')
                    break
                for _ in range(30):
                    if stop_ev.is_set(): break
                    time.sleep(1)
                continue

            fail_count = 0  # reset on success

            if cd > 0:
                acc['cooldown'] = cd
                add_log(acc_id, f"⏳ {PERKS[acc['perk']]['label']} — كمل {fmt(cd)}", 'warn')
                socketio.emit('update', get_state())
                # انتظر مع فحص كل ثانية
                waited = 0
                while waited < cd and not stop_ev.is_set():
                    time.sleep(1)
                    waited += 1
                    if acc['cooldown'] > 0:
                        acc['cooldown'] -= 1
                continue

            # جاهز للترقية!
            acc['cooldown'] = 0
            add_log(acc_id, f"⚡ {PERKS[acc['perk']]['label']} جاهز — جاري الترقية...", 'ok')
            success, result = do_upgrade(acc_id)

            if success:
                acc['upgrades'] += 1
                acc['last_upgrade'] = datetime.now().strftime('%H:%M:%S')
                acc['cooldown'] = 65
                add_log(acc_id, f"✅ تمت الترقية #{acc['upgrades']}!", 'ok')
                refresh_profile(acc_id)
            else:
                msg = str(result)[:60]
                add_log(acc_id, f"❌ فشل الترقية: {msg}", 'error')
                if 'Token منتهي' in msg:
                    acc['status'] = 'error'
                    acc['enabled'] = False
                    socketio.emit('update', get_state())
                    break
                acc['cooldown'] = 30
                for _ in range(30):
                    if stop_ev.is_set(): break
                    time.sleep(1)
                    if acc['cooldown'] > 0:
                        acc['cooldown'] -= 1

        except Exception as e:
            add_log(acc_id, f"💥 خطأ: {str(e)[:80]}", 'error')
            time.sleep(15)

    acc['status'] = 'stopped'
    acc['enabled'] = False
    add_log(acc_id, '⏹ البوت موقف', 'warn')
    socketio.emit('update', get_state())

# ── Scheduler ──────────────────────────────────────
scheduler = BackgroundScheduler()
def tick():
    socketio.emit('update', get_state())
scheduler.add_job(tick, 'interval', seconds=5)
scheduler.start()

# ── State ──────────────────────────────────────────
def get_state():
    return {k: {kk: vv for kk, vv in v.items() if kk != 'logs'}
            for k, v in accounts.items()}

def fmt(s):
    s = int(s)
    if s < 60: return f'{s}s'
    if s < 3600: return f'{s//60}m {s%60:02d}s'
    return f'{s//3600}h {(s%3600)//60}m'

# ── Routes ─────────────────────────────────────────
@app.route('/')
def index():
    return Response(HTML_PAGE, mimetype='text/html')

@app.route('/api/state')
def api_state():
    return jsonify(get_state())

@app.route('/api/logs/<acc_id>')
def api_logs(acc_id):
    return jsonify(accounts.get(acc_id, {}).get('logs', []))

@app.route('/api/start/<acc_id>', methods=['POST'])
def api_start(acc_id):
    if acc_id not in accounts: return jsonify({'error': 'not found'}), 404
    if not accounts[acc_id]['token']:
        return jsonify({'error': 'أضف Token أولاً من الإعدادات'}), 400
    if acc_id in bot_threads and bot_threads[acc_id].is_alive():
        return jsonify({'status': 'already running'})
    stop_events[acc_id] = threading.Event()
    t = threading.Thread(target=bot_loop, args=(acc_id, stop_events[acc_id]), daemon=True)
    bot_threads[acc_id] = t
    accounts[acc_id]['enabled'] = True
    t.start()
    return jsonify({'status': 'started'})

@app.route('/api/stop/<acc_id>', methods=['POST'])
def api_stop(acc_id):
    if acc_id in stop_events:
        stop_events[acc_id].set()
    accounts[acc_id]['enabled'] = False
    accounts[acc_id]['status'] = 'stopped'
    return jsonify({'status': 'stopped'})

@app.route('/api/refresh/<acc_id>', methods=['POST'])
def api_refresh(acc_id):
    if acc_id not in accounts: return jsonify({'error': 'not found'}), 404
    ok = refresh_profile(acc_id)
    return jsonify({'status': 'ok' if ok else 'failed'})

@app.route('/api/config/<acc_id>', methods=['POST'])
def api_config(acc_id):
    if acc_id not in accounts: return jsonify({'error': 'not found'}), 404
    data = request.json or {}
    if 'token' in data and data['token']:
        accounts[acc_id]['token'] = data['token'].strip()
    if 'perk' in data and data['perk'] in PERKS:
        accounts[acc_id]['perk'] = data['perk']
    if 'currency' in data and data['currency'] in ['money', 'diamond']:
        accounts[acc_id]['currency'] = data['currency']
    if 'name' in data and data['name']:
        accounts[acc_id]['name'] = data['name'][:30]
    add_log(acc_id, '⚙️ تم حفظ الإعدادات', 'info')
    return jsonify({'status': 'ok'})

# ── SocketIO ───────────────────────────────────────
@socketio.on('connect')
def on_connect():
    emit('update', get_state())
    for acc_id, acc in accounts.items():
        for entry in acc['logs'][:15]:
            emit('log', {'acc_id': acc_id, **entry})

# ── Main ───────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    log.info(f"🚀 Diplomacia Bot on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
