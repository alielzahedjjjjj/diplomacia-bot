"""
Diplomacia Auto Perk Bot - API Mode
بيكلم API الموقع مباشرة بدون browser
"""
import os, json, time, threading, logging, requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request
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

# ── State ──────────────────────────────────────────
accounts = {
    '1': {
        'id': '1', 'name': 'Cazirns', 'token': '',
        'enabled': False, 'status': 'stopped',
        'perk': 'scientist', 'currency': 'diamond',
        'cooldown': 0, 'upgrades': 0, 'last_upgrade': '—',
        'balance': '—', 'diamonds': '—',
        'level': {'barracks': '?', 'war_techniques': '?', 'scientist': '?'},
        'xp_pct': 0, 'logs': []
    },
    '2': {
        'id': '2', 'name': 'Hesap 2', 'token': '',
        'enabled': False, 'status': 'stopped',
        'perk': 'scientist', 'currency': 'diamond',
        'cooldown': 0, 'upgrades': 0, 'last_upgrade': '—',
        'balance': '—', 'diamonds': '—',
        'level': {'barracks': '?', 'war_techniques': '?', 'scientist': '?'},
        'xp_pct': 0, 'logs': []
    }
}
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
def headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0',
        'Origin': 'https://diplomacia.com.tr',
        'Referer': 'https://diplomacia.com.tr/',
    }

def api_get(token, path):
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers(token), timeout=15)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        log.error(f"GET {path} error: {e}")
        return None

def api_post(token, path, data=None):
    try:
        r = requests.post(f"{BASE_URL}{path}", headers=headers(token),
                          json=data or {}, timeout=15)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        log.error(f"POST {path} error: {e}")
        return 0, {}

# ── Refresh Profile ────────────────────────────────
def refresh_profile(acc_id):
    acc = accounts[acc_id]
    data = api_get(acc['token'], '/players/profile')
    if not data:
        return False
    try:
        player = data.get('player', data)
        acc['balance']  = f"${player.get('money', 0):,}"
        acc['diamonds'] = str(player.get('diamonds', 0))
        acc['name']     = player.get('username', acc['name'])
        xp_cur = player.get('experience', 0)
        xp_nxt = player.get('next_level_experience', 1)
        acc['xp_pct'] = round((xp_cur / max(xp_nxt, 1)) * 100)

        # مستويات البيركات
        skills = player.get('skills', {})
        if skills:
            acc['level']['barracks']       = skills.get('barracks', {}).get('level', '?')
            acc['level']['war_techniques'] = skills.get('war_techniques', {}).get('level', '?')
            acc['level']['scientist']      = skills.get('bilim_insani', skills.get('scientist', {}).get('level', '?')) if isinstance(skills.get('bilim_insani'), dict) else skills.get('bilim_insani', {}).get('level', '?')
        socketio.emit('update', get_state())
        return True
    except Exception as e:
        log.error(f"Profile parse error: {e}")
        return False

# ── Read Cooldown ──────────────────────────────────
def get_cooldown(acc_id):
    """اقرأ cooldown البيرك من الـ API"""
    acc = accounts[acc_id]
    perk_key = PERKS[acc['perk']]['key']

    # جرب endpoint البروفايل
    data = api_get(acc['token'], '/players/profile')
    if not data:
        return None

    try:
        player = data.get('player', data)
        skills = player.get('skills', {})

        skill = skills.get(perk_key) or skills.get(acc['perk'], {})
        if isinstance(skill, dict):
            # cooldown_remaining أو upgrade_end_time
            cd = skill.get('cooldown_remaining', 0) or skill.get('remaining_seconds', 0)
            if cd and cd > 0:
                return int(cd)

            end_time = skill.get('upgrade_end_time') or skill.get('upgrading_until')
            if end_time:
                import time as t
                remaining = int(end_time) - int(t.time())
                return max(0, remaining)
        return 0
    except Exception as e:
        log.error(f"Cooldown parse error: {e}")
        return 0

# ── Do Upgrade ─────────────────────────────────────
def do_upgrade(acc_id):
    acc = accounts[acc_id]
    perk_key = PERKS[acc['perk']]['key']
    currency = 'money' if acc['currency'] == 'money' else 'diamond'

    # جرب endpoints مختلفة
    endpoints = [
        f'/skills/{perk_key}/upgrade',
        f'/players/skills/{perk_key}/upgrade',
        f'/skills/upgrade',
    ]
    payload = {'skill': perk_key, 'currency': currency}

    for ep in endpoints:
        status, resp = api_post(acc['token'], ep, payload)
        log.info(f"Upgrade attempt {ep}: status={status} resp={resp}")
        if status in (200, 201):
            return True, resp
        if status == 400:
            msg = resp.get('message', '') if isinstance(resp, dict) else str(resp)
            if 'cooldown' in msg.lower() or 'wait' in msg.lower():
                return False, msg
            # 400 ممكن يكون payload خاطئ — جرب التالي
        if status == 404:
            continue  # endpoint مش صح — جرب التالي
    return False, 'all endpoints failed'

# ── Bot Loop ───────────────────────────────────────
def bot_loop(acc_id, stop_ev):
    acc = accounts[acc_id]
    add_log(acc_id, f"▶ البوت شغّال — {PERKS[acc['perk']]['label']}", 'ok')
    acc['status'] = 'running'

    # تحقق من التوكن أولاً
    if not acc['token']:
        add_log(acc_id, '❌ مفيش Token! أضف Token من الإعدادات', 'error')
        acc['status'] = 'error'
        acc['enabled'] = False
        socketio.emit('update', get_state())
        return

    # جلب البروفايل
    if refresh_profile(acc_id):
        add_log(acc_id, f"✅ متصل — {acc['name']} | {acc['balance']} | 💎{acc['diamonds']}", 'ok')
    else:
        add_log(acc_id, '⚠️ Token منتهي أو خاطئ', 'warn')
        acc['status'] = 'error'
        acc['enabled'] = False
        socketio.emit('update', get_state())
        return

    while not stop_ev.is_set():
        try:
            cd = get_cooldown(acc_id)

            if cd is None:
                add_log(acc_id, '⚠️ مش قادر يقرأ الحالة', 'warn')
                acc['cooldown'] = 0
                for _ in range(30):
                    if stop_ev.is_set(): break
                    time.sleep(1)
                continue

            if cd > 0:
                acc['cooldown'] = cd
                add_log(acc_id, f"⏳ {PERKS[acc['perk']]['label']} — كمل {fmt(cd)}", 'warn')
                socketio.emit('update', get_state())
                # انتظر الـ cooldown مع فحص كل ثانية
                for _ in range(min(cd, 60)):
                    if stop_ev.is_set(): break
                    time.sleep(1)
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
                acc['cooldown'] = 62
                add_log(acc_id, f"✅ تمت الترقية! إجمالي: {acc['upgrades']}", 'ok')
                refresh_profile(acc_id)
            else:
                add_log(acc_id, f"❌ فشل الترقية: {str(result)[:60]}", 'error')
                acc['cooldown'] = 30
                for _ in range(30):
                    if stop_ev.is_set(): break
                    time.sleep(1)

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
    return render_template('index.html')

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
        return jsonify({'error': 'أضف Token أولاً'}), 400
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
    if 'name' in data:
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
    # حمّل tokens من environment variables لو موجودة
    for i in ['1', '2']:
        t = os.environ.get(f'TOKEN_{i}', '')
        if t: accounts[i]['token'] = t
        n = os.environ.get(f'NAME_{i}', '')
        if n: accounts[i]['name'] = n

    port = int(os.environ.get('PORT', 8080))
    log.info(f"🚀 Diplomacia Bot on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
