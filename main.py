"""
Diplomacia Bot - Multi User System
كل يوزر عنده حساباته الخاصة
"""
import os, time, threading, logging, requests, sqlite3, hashlib, secrets
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, redirect
from flask_socketio import SocketIO, emit, join_room
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'diplo-secret-2024')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

BASE_URL = "https://diplomacia.com.tr/api"
PERKS = {
    'barracks':       {'label': 'BARRACKS',       'key': 'barracks'},
    'war_techniques': {'label': 'WAR TECHNIQUES', 'key': 'war_techniques'},
    'scientist':      {'label': 'SCIENTIST',       'key': 'bilim_insani'},
}

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

# ── Database ───────────────────────────────────────
def get_db():
    db = sqlite3.connect('bot.db', check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            slot INTEGER NOT NULL,
            name TEXT DEFAULT 'حساب',
            token TEXT DEFAULT '',
            perk TEXT DEFAULT 'scientist',
            currency TEXT DEFAULT 'diamond',
            upgrades INTEGER DEFAULT 0,
            last_upgrade TEXT DEFAULT '—',
            FOREIGN KEY(user_id) REFERENCES users(id),
            UNIQUE(user_id, slot)
        );
    ''')
    db.commit()
    db.close()

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ── In-memory bot state ────────────────────────────
# { user_id: { slot: { status, cooldown, balance, diamonds, xp_pct, level, logs } } }
bot_state = {}
stop_events = {}
bot_threads = {}

def get_user_state(user_id):
    if user_id not in bot_state:
        bot_state[user_id] = {
            1: new_slot_state(),
            2: new_slot_state(),
        }
    return bot_state[user_id]

def new_slot_state():
    return {
        'status': 'stopped', 'cooldown': 0,
        'balance': '—', 'diamonds': '—', 'xp_pct': 0,
        'level': {'barracks': '?', 'war_techniques': '?', 'scientist': '?'},
        'logs': []
    }

# ── Helpers ────────────────────────────────────────
def add_log(user_id, slot, msg, level='info'):
    state = get_user_state(user_id)[slot]
    ts = datetime.now().strftime('%H:%M:%S')
    entry = {'time': ts, 'msg': msg, 'level': level}
    state['logs'].insert(0, entry)
    state['logs'] = state['logs'][:60]
    room = f'user_{user_id}'
    socketio.emit('log', {'slot': slot, **entry}, to=room)
    socketio.emit('update', get_full_state(user_id), to=room)

def api_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/148.0.0.0',
        'Origin': 'https://diplomacia.com.tr',
        'Referer': 'https://diplomacia.com.tr/',
    }

def api_get(token, path):
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=api_headers(token), timeout=15)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        log.error(f"GET {path}: {e}")
        return None

def api_post(token, path, data=None):
    try:
        r = requests.post(f"{BASE_URL}{path}", headers=api_headers(token), json=data or {}, timeout=15)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        log.error(f"POST {path}: {e}")
        return 0, {}

def fmt(s):
    s = int(s)
    if s < 60: return f'{s}s'
    if s < 3600: return f'{s//60}m {s%60:02d}s'
    return f'{s//3600}h {(s%3600)//60}m'

def get_full_state(user_id):
    db = get_db()
    accs = db.execute('SELECT * FROM accounts WHERE user_id=?', (user_id,)).fetchall()
    db.close()
    state = get_user_state(user_id)
    result = {}
    for acc in accs:
        slot = acc['slot']
        s = state.get(slot, new_slot_state())
        result[slot] = {
            'slot': slot, 'name': acc['name'], 'token': '***' if acc['token'] else '',
            'perk': acc['perk'], 'currency': acc['currency'],
            'upgrades': acc['upgrades'], 'last_upgrade': acc['last_upgrade'],
            'status': s['status'], 'cooldown': s['cooldown'],
            'balance': s['balance'], 'diamonds': s['diamonds'],
            'xp_pct': s['xp_pct'], 'level': s['level'],
        }
    return result

# ── Bot Logic ──────────────────────────────────────
def refresh_profile(user_id, slot, token):
    data = api_get(token, '/players/profile')
    if not data: return False
    try:
        p = data.get('player', data)
        s = get_user_state(user_id)[slot]
        s['balance']  = f"${p.get('money', 0):,}"
        s['diamonds'] = str(p.get('diamonds', 0))
        xp_cur = p.get('experience', 0)
        xp_nxt = p.get('next_level_experience', 1)
        s['xp_pct'] = round((xp_cur / max(xp_nxt, 1)) * 100)
        skills = p.get('skills', {})
        if skills:
            s['level']['barracks']       = skills.get('barracks', {}).get('level', '?')
            s['level']['war_techniques'] = skills.get('war_techniques', {}).get('level', '?')
            bi = skills.get('bilim_insani', {})
            s['level']['scientist'] = bi.get('level', '?') if isinstance(bi, dict) else '?'
        # update name in db
        uname = p.get('username')
        if uname:
            db = get_db()
            db.execute('UPDATE accounts SET name=? WHERE user_id=? AND slot=?', (uname, user_id, slot))
            db.commit()
            db.close()
        return True
    except Exception as e:
        log.error(f"Profile parse: {e}")
        return False

def get_cooldown(token, perk):
    data = api_get(token, '/players/profile')
    if not data: return None
    try:
        p = data.get('player', data)
        skills = p.get('skills', {})
        perk_key = PERKS[perk]['key']
        skill = skills.get(perk_key) or skills.get(perk, {})
        if isinstance(skill, dict):
            cd = skill.get('cooldown_remaining', 0) or skill.get('remaining_seconds', 0)
            if cd and cd > 0: return int(cd)
            end = skill.get('upgrade_end_time') or skill.get('upgrading_until')
            if end:
                remaining = int(end) - int(time.time())
                return max(0, remaining)
        return 0
    except:
        return 0

def do_upgrade(token, perk, currency):
    perk_key = PERKS[perk]['key']
    curr = 'money' if currency == 'money' else 'diamond'
    payload = {'skill': perk_key, 'currency': curr}
    for ep in [f'/skills/{perk_key}/upgrade', f'/players/skills/{perk_key}/upgrade', '/skills/upgrade']:
        status, resp = api_post(token, ep, payload)
        if status in (200, 201): return True, resp
        if status == 404: continue
        if status == 400:
            msg = resp.get('message', '') if isinstance(resp, dict) else str(resp)
            if 'cooldown' in msg.lower(): return False, msg
    return False, 'failed'

def bot_loop(user_id, slot, stop_ev):
    db = get_db()
    acc = db.execute('SELECT * FROM accounts WHERE user_id=? AND slot=?', (user_id, slot)).fetchone()
    db.close()
    if not acc or not acc['token']:
        add_log(user_id, slot, '❌ مفيش Token!', 'error')
        get_user_state(user_id)[slot]['status'] = 'error'
        return

    token = acc['token']
    perk  = acc['perk']
    curr  = acc['currency']

    add_log(user_id, slot, f"▶ البوت شغّال — {PERKS[perk]['label']}", 'ok')
    get_user_state(user_id)[slot]['status'] = 'running'

    if refresh_profile(user_id, slot, token):
        s = get_user_state(user_id)[slot]
        add_log(user_id, slot, f"✅ متصل | {s['balance']} | 💎{s['diamonds']}", 'ok')
    else:
        add_log(user_id, slot, '⚠️ Token منتهي أو خاطئ', 'warn')
        get_user_state(user_id)[slot]['status'] = 'error'
        return

    while not stop_ev.is_set():
        try:
            cd = get_cooldown(token, perk)
            s  = get_user_state(user_id)[slot]
            if cd is None:
                add_log(user_id, slot, '⚠️ مش قادر يقرأ الحالة', 'warn')
                for _ in range(30):
                    if stop_ev.is_set(): break
                    time.sleep(1)
                continue
            if cd > 0:
                s['cooldown'] = cd
                add_log(user_id, slot, f"⏳ كمل {fmt(cd)}", 'warn')
                for _ in range(min(cd, 60)):
                    if stop_ev.is_set(): break
                    time.sleep(1)
                    if s['cooldown'] > 0: s['cooldown'] -= 1
                continue
            s['cooldown'] = 0
            add_log(user_id, slot, f"⚡ {PERKS[perk]['label']} جاهز — جاري الترقية...", 'ok')
            success, result = do_upgrade(token, perk, curr)
            if success:
                db = get_db()
                db.execute('UPDATE accounts SET upgrades=upgrades+1, last_upgrade=? WHERE user_id=? AND slot=?',
                           (datetime.now().strftime('%H:%M:%S'), user_id, slot))
                db.commit()
                db.close()
                s['cooldown'] = 62
                add_log(user_id, slot, f"✅ تمت الترقية!", 'ok')
                refresh_profile(user_id, slot, token)
            else:
                add_log(user_id, slot, f"❌ فشل: {str(result)[:60]}", 'error')
                for _ in range(30):
                    if stop_ev.is_set(): break
                    time.sleep(1)
        except Exception as e:
            add_log(user_id, slot, f"💥 خطأ: {str(e)[:80]}", 'error')
            time.sleep(15)

    get_user_state(user_id)[slot]['status'] = 'stopped'
    add_log(user_id, slot, '⏹ البوت موقف', 'warn')

# ── Auth ───────────────────────────────────────────
def current_user():
    return session.get('user_id'), session.get('username')

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ── Routes ─────────────────────────────────────────
@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username=? AND password=?',
                          (username, hash_pass(password))).fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            # ensure 2 slots exist
            db = get_db()
            for slot in [1, 2]:
                db.execute('INSERT OR IGNORE INTO accounts(user_id, slot) VALUES(?,?)', (user['id'], slot))
            db.commit()
            db.close()
            return jsonify({'ok': True})
        return jsonify({'ok': False, 'error': 'اسم مستخدم أو كلمة سر خاطئة'}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ── Admin ──────────────────────────────────────────
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        data = request.json or {}
        if data.get('admin_user') != ADMIN_USER or data.get('admin_pass') != ADMIN_PASS:
            return jsonify({'ok': False, 'error': 'خاطئ'}), 403
        action = data.get('action')
        if action == 'add_user':
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            if not username or not password:
                return jsonify({'ok': False, 'error': 'ادخل اسم وكلمة سر'})
            try:
                db = get_db()
                db.execute('INSERT INTO users(username, password) VALUES(?,?)', (username, hash_pass(password)))
                db.commit()
                db.close()
                return jsonify({'ok': True, 'msg': f'تم إضافة {username}'})
            except:
                return jsonify({'ok': False, 'error': 'الاسم موجود بالفعل'})
        if action == 'list_users':
            db = get_db()
            users = db.execute('SELECT id, username, created_at FROM users').fetchall()
            db.close()
            return jsonify({'ok': True, 'users': [dict(u) for u in users]})
        if action == 'delete_user':
            uid = data.get('user_id')
            db = get_db()
            db.execute('DELETE FROM accounts WHERE user_id=?', (uid,))
            db.execute('DELETE FROM users WHERE id=?', (uid,))
            db.commit()
            db.close()
            return jsonify({'ok': True})
    return render_template('admin.html')

# ── API ────────────────────────────────────────────
@app.route('/api/state')
@login_required
def api_state():
    user_id = session['user_id']
    return jsonify(get_full_state(user_id))

@app.route('/api/logs/<int:slot>')
@login_required
def api_logs(slot):
    user_id = session['user_id']
    logs = get_user_state(user_id).get(slot, {}).get('logs', [])
    return jsonify(logs)

@app.route('/api/start/<int:slot>', methods=['POST'])
@login_required
def api_start(slot):
    user_id = session['user_id']
    db = get_db()
    acc = db.execute('SELECT * FROM accounts WHERE user_id=? AND slot=?', (user_id, slot)).fetchone()
    db.close()
    if not acc or not acc['token']:
        return jsonify({'error': 'أضف Token أولاً'}), 400
    key = f'{user_id}_{slot}'
    if key in bot_threads and bot_threads[key].is_alive():
        return jsonify({'status': 'already running'})
    stop_events[key] = threading.Event()
    t = threading.Thread(target=bot_loop, args=(user_id, slot, stop_events[key]), daemon=True)
    bot_threads[key] = t
    t.start()
    return jsonify({'status': 'started'})

@app.route('/api/stop/<int:slot>', methods=['POST'])
@login_required
def api_stop(slot):
    user_id = session['user_id']
    key = f'{user_id}_{slot}'
    if key in stop_events:
        stop_events[key].set()
    get_user_state(user_id)[slot]['status'] = 'stopped'
    return jsonify({'status': 'stopped'})

@app.route('/api/config/<int:slot>', methods=['POST'])
@login_required
def api_config(slot):
    user_id = session['user_id']
    data = request.json or {}
    db = get_db()
    if 'token' in data and data['token']:
        db.execute('UPDATE accounts SET token=? WHERE user_id=? AND slot=?', (data['token'].strip(), user_id, slot))
    if 'perk' in data and data['perk'] in PERKS:
        db.execute('UPDATE accounts SET perk=? WHERE user_id=? AND slot=?', (data['perk'], user_id, slot))
    if 'currency' in data and data['currency'] in ['money', 'diamond']:
        db.execute('UPDATE accounts SET currency=? WHERE user_id=? AND slot=?', (data['currency'], user_id, slot))
    if 'name' in data:
        db.execute('UPDATE accounts SET name=? WHERE user_id=? AND slot=?', (data['name'][:30], user_id, slot))
    db.commit()
    db.close()
    add_log(user_id, slot, '⚙️ تم حفظ الإعدادات', 'info')
    return jsonify({'status': 'ok'})

# ── SocketIO ───────────────────────────────────────
@socketio.on('connect')
def on_connect():
    user_id = session.get('user_id')
    if not user_id: return
    join_room(f'user_{user_id}')
    emit('update', get_full_state(user_id))
    for slot in [1, 2]:
        for entry in get_user_state(user_id).get(slot, {}).get('logs', [])[:10]:
            emit('log', {'slot': slot, **entry})

# ── Scheduler ──────────────────────────────────────
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: None, 'interval', seconds=10)
scheduler.start()

# ── Main ───────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    log.info(f"🚀 Diplomacia Multi-User Bot on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
