"""
Diplomacia Bot - Multi User System
كل يوزر عنده حساباته الخاصة
"""
import os, time, threading, logging, requests, sqlite3, hashlib, secrets
from datetime import datetime
from flask import Flask, jsonify, request, session, redirect, Response
from flask_socketio import SocketIO, emit, join_room
from apscheduler.schedulers.background import BackgroundScheduler

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Diplomacia Bot — دخول</title>
<style>
:root{--gold:#c8a84b;--bg:#07071a;--card:#0f0f2e}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:var(--bg);color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{background:var(--card);border:1px solid #1a1a4e;border-radius:16px;padding:40px 32px;width:100%;max-width:380px}
h1{text-align:center;color:var(--gold);font-size:1.4rem;margin-bottom:8px;letter-spacing:2px}
p{text-align:center;color:#888;font-size:.85rem;margin-bottom:28px}
label{display:block;font-size:.8rem;color:#aaa;margin-bottom:6px}
input{width:100%;background:#0a0a25;border:1px solid #2a2a5e;border-radius:8px;padding:12px;color:#fff;font-size:.95rem;margin-bottom:16px;outline:none}
input:focus{border-color:var(--gold)}
button{width:100%;background:var(--gold);color:#000;border:none;border-radius:8px;padding:13px;font-size:1rem;font-weight:700;cursor:pointer;margin-top:4px}
button:hover{opacity:.9}
.err{color:#ff5555;font-size:.85rem;text-align:center;margin-top:12px;display:none}
.logo{text-align:center;font-size:2rem;margin-bottom:12px}
</style>
</head>
<body>
<div class="box">
  <div class="logo">⚔️</div>
  <h1>DIPLOMACIA BOT</h1>
  <p>سجّل دخولك للمتابعة</p>
  <label>اسم المستخدم</label>
  <input id="u" type="text" placeholder="username">
  <label>كلمة السر</label>
  <input id="p" type="password" placeholder="••••••••">
  <button onclick="login()">دخول ▶</button>
  <div class="err" id="err"></div>
</div>
<script>
async function login(){
  const u=document.getElementById('u').value.trim();
  const p=document.getElementById('p').value;
  if(!u||!p){showErr('ادخل اسم المستخدم وكلمة السر');return}
  const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
  const d=await r.json();
  if(d.ok) window.location='/';
  else showErr(d.error||'خطأ');
}
function showErr(m){const e=document.getElementById('err');e.textContent=m;e.style.display='block'}
document.addEventListener('keydown',e=>{if(e.key==='Enter')login()});
</script>
</body>
</html>
"""
ADMIN_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Panel</title>
<style>
:root{--gold:#c8a84b;--bg:#07071a;--card:#0f0f2e}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:var(--bg);color:#fff;min-height:100vh;padding:20px}
h1{color:var(--gold);text-align:center;margin-bottom:24px;letter-spacing:2px}
.box{background:var(--card);border:1px solid #1a1a4e;border-radius:12px;padding:24px;max-width:500px;margin:0 auto 20px}
h2{color:#aaa;font-size:.95rem;margin-bottom:16px}
input{width:100%;background:#0a0a25;border:1px solid #2a2a5e;border-radius:8px;padding:10px;color:#fff;font-size:.9rem;margin-bottom:10px;outline:none}
input:focus{border-color:var(--gold)}
button{background:var(--gold);color:#000;border:none;border-radius:8px;padding:10px 20px;font-weight:700;cursor:pointer;margin-left:8px}
button.red{background:#c0392b;color:#fff}
.msg{margin-top:10px;font-size:.85rem;color:#4caf50}
.err{color:#ff5555;font-size:.85rem;margin-top:8px}
table{width:100%;border-collapse:collapse;margin-top:12px}
th{color:var(--gold);font-size:.8rem;padding:8px;border-bottom:1px solid #1a1a4e;text-align:right}
td{padding:8px;border-bottom:1px solid #1a1a3e;font-size:.85rem}
#login-box{max-width:400px;margin:60px auto}
</style>
</head>
<body>
<div id="login-box" class="box">
  <h1>⚙️ ADMIN</h1>
  <input id="au" placeholder="Admin Username">
  <input id="ap" type="password" placeholder="Admin Password">
  <button onclick="adminLogin()">دخول</button>
  <div class="err" id="lerr"></div>
</div>

<div id="panel" style="display:none;max-width:500px;margin:0 auto">
  <h1>⚙️ لوحة الإدارة</h1>

  <div class="box">
    <h2>➕ إضافة مستخدم جديد</h2>
    <input id="nu" placeholder="اسم المستخدم">
    <input id="np" type="password" placeholder="كلمة السر">
    <button onclick="addUser()">إضافة</button>
    <div class="msg" id="amsg"></div>
  </div>

  <div class="box">
    <h2>👥 المستخدمين</h2>
    <button onclick="loadUsers()" style="background:#1a1a4e;color:#aaa;margin-bottom:12px">تحديث</button>
    <table>
      <tr><th>اسم المستخدم</th><th>تاريخ الإضافة</th><th>حذف</th></tr>
      <tbody id="users-list"></tbody>
    </table>
  </div>
</div>

<script>
let AU='', AP='';

function adminLogin(){
  AU=document.getElementById('au').value;
  AP=document.getElementById('ap').value;
  loadUsers();
}

async function loadUsers(){
  const r=await fetch('/admin',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({admin_user:AU,admin_pass:AP,action:'list_users'})});
  if(r.status===403){document.getElementById('lerr').textContent='بيانات خاطئة';return}
  const d=await r.json();
  document.getElementById('login-box').style.display='none';
  document.getElementById('panel').style.display='block';
  const tbody=document.getElementById('users-list');
  tbody.innerHTML=d.users.map(u=>`
    <tr>
      <td>${u.username}</td>
      <td>${u.created_at?.split('T')[0]||'—'}</td>
      <td><button class="red" onclick="deleteUser(${u.id},'${u.username}')">حذف</button></td>
    </tr>`).join('');
}

async function addUser(){
  const nu=document.getElementById('nu').value.trim();
  const np=document.getElementById('np').value;
  const r=await fetch('/admin',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({admin_user:AU,admin_pass:AP,action:'add_user',username:nu,password:np})});
  const d=await r.json();
  const msg=document.getElementById('amsg');
  msg.textContent=d.ok?d.msg:d.error;
  msg.style.color=d.ok?'#4caf50':'#ff5555';
  if(d.ok){document.getElementById('nu').value='';document.getElementById('np').value='';loadUsers()}
}

async function deleteUser(id,name){
  if(!confirm(`حذف ${name}؟`))return;
  await fetch('/admin',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({admin_user:AU,admin_pass:AP,action:'delete_user',user_id:id})});
  loadUsers();
}
</script>
</body>
</html>
"""
INDEX_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Diplomacia Bot</title>
<style>.logout-btn{position:fixed;top:10px;left:10px;background:#c0392b;color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:.8rem;cursor:pointer;z-index:999}</style>
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
@media(max-width:600px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<button class="logout-btn" onclick="window.location='/logout'">خروج ↩</button>
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
      <input class="inp" id="tok1-name" placeholder="اسم الحساب (اختياري)">
      <input class="inp" id="tok1" placeholder="Token الحساب الأول (eyJhbG...)">
      <button class="btn btn-g" style="width:100%;margin-bottom:1rem" onclick="saveToken('1')">💾 حفظ الحساب 1</button>

      <div style="font-size:12px;color:var(--muted);margin-bottom:.7rem">حساب 2</div>
      <input class="inp" id="tok2-name" placeholder="اسم الحساب (اختياري)">
      <input class="inp" id="tok2" placeholder="Token الحساب الثاني (eyJhbG...)">
      <button class="btn btn-g" style="width:100%;margin-bottom:1rem" onclick="saveToken('2')">💾 حفظ الحساب 2</button>
    </div>
  </div>

  <div style="font-size:.7rem;color:rgba(200,168,75,.6);letter-spacing:2px;margin-bottom:.7rem">ملاحظات</div>
  <div class="log-panel">
    <div style="padding:.9rem 1rem;font-size:12px;line-height:2;color:var(--muted)">
      <div>⏱ Token بيخلص بعد ~7 أيام — جدده من هنا</div>
      <div>🔒 Token محفوظ في الـ environment variables على السيرفر</div>
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
let cdTimers = {};

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
    const lvl = acc.level?.[key] !== undefined ? acc.level[key] : '?';
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

  return `<div class="card ${stClass}" id="card-${id}">
    <div class="ch">
      <div class="av" style="overflow:hidden;padding:0;position:relative">
        ${acc.avatar 
          ? `<img src="${acc.avatar}" style="width:100%;height:100%;object-fit:cover;border-radius:50%" onerror="this.parentElement.innerHTML='🎮'">`
          : '🎮'}
        ${acc.flag ? `<img src="${acc.flag}" style="position:absolute;bottom:0;right:0;width:14px;height:14px;border-radius:2px">` : ''}
      </div>
      <div style="flex:1;min-width:0">
        <div class="cn">${acc.name} <span style="font-size:10px;color:var(--muted)">Lv.${acc.player_level||'?'}</span></div>
        <div class="cs">${acc.rank ? acc.rank.replace('levelTitles.','') + ' | ' : ''}ترقيات: ${acc.upgrades}</div>
      </div>
      ${badge}
    </div>
    <div class="cb">
      <div class="res">
        <div class="rc">💵 <span>${acc.balance}</span></div>
        <div class="rc">💎 <span>${acc.diamonds}</span></div>
      </div>
      <div class="xb"><div class="xf" style="width:${xpPct}%"></div></div>
      <div class="slbl">اختر البيرك</div>
      <div class="cur">
        <button class="cb2 ${acc.currency==='money'?'act':''}" onclick="selCur('${id}','money')">💵 Money</button>
        <button class="cb2 ${acc.currency==='diamond'?'act':''}" onclick="selCur('${id}','diamond')">💎 Diamond</button>
      </div>
      <div class="prks">${perksHtml}</div>
      ${cdText}
    </div>
    <div class="ctrl">
      ${acc.enabled
        ? `<button class="btn btn-x" onclick="stopAcc('${id}')">⏹ إيقاف</button>`
        : `<button class="btn btn-s" onclick="startAcc('${id}')">▶ تشغيل</button>`}
      <button class="btn" onclick="switchPage('settings',document.getElementById('nav-settings'))">🔑 Token</button>
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
  if (r.ok) {
    alert(`✅ تم حفظ Token الحساب ${id}`);
    document.getElementById(`tok${id}`).value = '';
  }
}

// ── Log ──────────────────────────────────────────
const names = {'1':'Cazirns', '2':'Hesap2'};
function addLogEntry(e) {
  const body = document.getElementById('log-body');
  const div = document.createElement('div');
  div.className = `ll ${e.level}`;
  div.innerHTML = `<span class="lt2">${e.time}</span><span class="la">[${state[e.slot]?.name || e.slot}]</span><span class="lm">${e.msg}</span>`;
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
</html>
"""

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
    db = sqlite3.connect(os.environ.get('DB_PATH', '/data/bot.db'), check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    os.makedirs(os.path.dirname(os.environ.get('DB_PATH', '/data/bot.db')), exist_ok=True)
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
            avatar TEXT DEFAULT '',
            rank TEXT DEFAULT '',
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
        avatar = p.get('avatar', '') or p.get('profile_image', '') or p.get('image', '')
        rank = p.get('rank', '') or p.get('title', '') or p.get('military_rank', '')
        if uname:
            db = get_db()
            db.execute('UPDATE accounts SET name=?, avatar=?, rank=? WHERE user_id=? AND slot=?', 
                      (uname, avatar, rank, user_id, slot))
            db.commit()
            db.close()
            s['avatar'] = avatar
            s['rank'] = rank
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
    return Response(INDEX_HTML, mimetype='text/html')

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
    return Response(LOGIN_HTML, mimetype='text/html')

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
    return Response(ADMIN_HTML, mimetype='text/html')

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
    # لو في token جديد — اجلب بيانات الحساب تلقائي
    if 'token' in data and data['token']:
        token = data['token'].strip()
        def fetch_on_save():
            if refresh_profile(user_id, slot, token):
                s = get_user_state(user_id)[slot]
                add_log(user_id, slot, f"✅ تم ربط الحساب | {s['balance']} | 💎{s['diamonds']}", 'ok')
            else:
                add_log(user_id, slot, '⚠️ Token خاطئ أو منتهي', 'warn')
        import threading as _t
        _t.Thread(target=fetch_on_save, daemon=True).start()
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
