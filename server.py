#!/usr/bin/env python3
import argparse, json, os, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data.json')
LOCK = threading.Lock()

def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')

def load():
    if not os.path.exists(DATA):
        s = {'messages': [], 'tasks': [], 'events': []}
        save(s); return s
    with open(DATA) as f: return json.load(f)

def save(s):
    tmp = DATA + '.tmp'
    with open(tmp,'w') as f: json.dump(s,f,ensure_ascii=False,indent=2)
    os.replace(tmp, DATA)

def event(s, who, what):
    s['events'].insert(0, {'at': now(), 'who': who, 'what': what})
    s['events'] = s['events'][:200]

HTML = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>VIKI Ops Panel</title>
<style>
:root{--bg:#0b1220;--card:#121c2f;--muted:#8ba0c2;--text:#e8eefc;--line:#243457;--ok:#1f8f5f;--warn:#b7791f;--bad:#b42318;--info:#2b6cb0}
*{box-sizing:border-box} body{margin:0;font:14px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:linear-gradient(180deg,#08101d,#0b1220);color:var(--text)}
header{padding:14px 16px;border-bottom:1px solid var(--line);position:sticky;top:0;background:#0b1220cc;backdrop-filter:blur(6px)}
h1{margin:0;font-size:18px} .sub{color:var(--muted);font-size:12px}
main{display:grid;grid-template-columns:1fr 1.2fr;gap:12px;padding:12px}
@media(max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.card h2{margin:0;padding:10px 12px;font-size:14px;border-bottom:1px solid var(--line)}
.pad{padding:10px 12px}
.row{display:flex;gap:8px;flex-wrap:wrap}
input,select,textarea,button{font:inherit;border-radius:8px;border:1px solid var(--line);background:#0e1830;color:var(--text);padding:8px}
input,select,textarea{width:100%} textarea{min-height:54px;resize:vertical}
button{cursor:pointer;background:#17305f} button:hover{filter:brightness(1.1)}
#msgs{height:46vh;overflow:auto;padding:10px 12px;display:flex;flex-direction:column;gap:8px}
.msg{border:1px solid var(--line);border-radius:10px;padding:8px;background:#0d1730}
.meta{color:var(--muted);font-size:12px;margin-bottom:3px}
table{width:100%;border-collapse:collapse} th,td{border-bottom:1px solid var(--line);padding:8px;vertical-align:top;text-align:left;font-size:13px}
.pill{padding:2px 8px;border-radius:999px;font-size:12px;display:inline-block}
.todo{background:#2b6cb033;color:#93c5fd}.doing{background:#b7791f33;color:#fbd38d}.done{background:#1f8f5f33;color:#86efac}.blocked{background:#b4231833;color:#fca5a5}
a{color:#93c5fd;word-break:break-all}
.small{color:var(--muted);font-size:12px}
</style></head><body>
<header><h1>VIKI Ops Panel</h1><div class="sub">Chat + tablero local para León, VIKI y OpenCode. Actualiza cada 2 s.</div></header>
<main>
  <section class="card"><h2>Chat</h2>
    <div id="msgs"></div>
    <div class="pad">
      <div class="row"><select id="author"><option>León</option><option selected>VIKI</option><option>OpenCode</option></select></div>
      <div class="row" style="margin-top:8px"><textarea id="mtext" placeholder="Mensaje o resumen..."></textarea></div>
      <div class="row" style="margin-top:8px"><button onclick="sendMsg()">Enviar</button></div>
    </div>
  </section>
  <section class="card"><h2>Tablero de tareas</h2>
    <div class="pad">
      <div class="row"><input id="ttitle" placeholder="Nueva tarea"/></div>
      <div class="row" style="margin-top:8px">
        <select id="towner"><option>OpenCode</option><option>VIKI</option><option>León</option></select>
        <select id="tstatus"><option value="todo">pendiente</option><option value="doing">en progreso</option><option value="done">hecho</option><option value="blocked">bloqueado</option></select>
      </div>
      <div class="row" style="margin-top:8px"><input id="tlink" placeholder="Link (opcional)"/></div>
      <div class="row" style="margin-top:8px"><input id="tnote" placeholder="Nota/progreso (opcional)"/></div>
      <div class="row" style="margin-top:8px"><button onclick="addTask()">Agregar tarea</button></div>
    </div>
    <div class="pad" style="padding-top:0"><table><thead><tr><th>Tarea</th><th>Estado</th><th>Resp.</th><th>Link/Nota</th><th>Acción</th></tr></thead><tbody id="tasks"></tbody></table></div>
    <div class="pad small" id="events"></div>
  </section>
</main>
<script>
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
const labels={todo:'pendiente',doing:'en progreso',done:'hecho',blocked:'bloqueado'};
async function api(p,o){const r=await fetch(p,{headers:{'Content-Type':'application/json'},...o}); return r.json()}
async function refresh(){
  const s=await api('/api/state');
  const m=document.getElementById('msgs'); const atBottom=m.scrollTop+m.clientHeight>=m.scrollHeight-20;
  m.innerHTML=s.messages.slice().reverse().map(x=>`<div class="msg"><div class="meta">${esc(x.at)} · <b>${esc(x.author)}</b></div><div>${esc(x.text).replace(/\n/g,'<br>')}</div></div>`).join('');
  if(atBottom) m.scrollTop=m.scrollHeight;
  document.getElementById('tasks').innerHTML=s.tasks.map(t=>`<tr><td><b>${esc(t.title)}</b><div class="small">${esc(t.updated_at||'')}</div></td><td><span class="pill ${t.status}">${labels[t.status]||t.status}</span></td><td>${esc(t.owner||'')}</td><td>${t.link?`<a href="${esc(t.link)}" target="_blank">abrir</a><br>`:''}<span class="small">${esc(t.note||'')}</span></td><td><select onchange="upd('${t.id}',this.value)"><option value="">cambiar...</option><option value="todo">pendiente</option><option value="doing">en progreso</option><option value="done">hecho</option><option value="blocked">bloqueado</option></select></td></tr>`).join('');
  document.getElementById('events').innerHTML='<b>Bitácora:</b><br>'+s.events.slice(0,8).map(e=>`${esc(e.at)} — ${esc(e.who)}: ${esc(e.what)}`).join('<br>');
}
async function sendMsg(){const author=document.getElementById('author').value,text=document.getElementById('mtext').value.trim(); if(!text) return; await api('/api/messages',{method:'POST',body:JSON.stringify({author,text})}); document.getElementById('mtext').value=''; refresh();}
async function addTask(){const title=document.getElementById('ttitle').value.trim(); if(!title) return; await api('/api/tasks',{method:'POST',body:JSON.stringify({title,owner:document.getElementById('towner').value,status:document.getElementById('tstatus').value,link:document.getElementById('tlink').value.trim(),note:document.getElementById('tnote').value.trim(),author:document.getElementById('author').value})}); ['ttitle','tlink','tnote'].forEach(id=>document.getElementById(id).value=''); refresh();}
async function upd(id,status){if(!status) return; await api('/api/tasks/'+id,{method:'PATCH',body:JSON.stringify({status,author:document.getElementById('author').value})}); refresh();}
refresh(); setInterval(refresh,2000);
</script></body></html>'''

class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/api/state':
            with LOCK: self._json(200, load()); return
        if p in ('/','/index.html'):
            b=HTML.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
        self._json(404,{'error':'not found'})
    def do_POST(self):
        p=urlparse(self.path).path; n=int(self.headers.get('Content-Length','0') or 0); body=self.rfile.read(n) if n else b'{}'
        try: data=json.loads(body.decode() or '{}')
        except: return self._json(400,{'error':'bad json'})
        with LOCK:
            s=load()
            if p=='/api/messages':
                author=(data.get('author') or 'VIKI')[:40]; text=(data.get('text') or '').strip()
                if not text: return self._json(400,{'error':'text required'})
                m={'id':uuid.uuid4().hex[:10],'at':now(),'author':author,'text':text[:4000]}
                s['messages'].append(m); s['messages']=s['messages'][-500:]; event(s,author,f"mensaje: {text[:80]}"); save(s); return self._json(200,m)
            if p=='/api/tasks':
                title=(data.get('title') or '').strip()
                if not title: return self._json(400,{'error':'title required'})
                author=(data.get('author') or 'VIKI')[:40]
                t={'id':uuid.uuid4().hex[:10],'title':title[:200],'owner':(data.get('owner') or 'OpenCode')[:40],'status':data.get('status') or 'todo','link':(data.get('link') or '')[:500],'note':(data.get('note') or '')[:1000],'created_at':now(),'updated_at':now()}
                if t['status'] not in ('todo','doing','done','blocked'): t['status']='todo'
                s['tasks'].insert(0,t); event(s,author,f"tarea creada: {t['title']} [{t['status']}]"); save(s); return self._json(200,t)
        self._json(404,{'error':'not found'})
    def do_PATCH(self):
        p=urlparse(self.path).path; n=int(self.headers.get('Content-Length','0') or 0); body=self.rfile.read(n) if n else b'{}'
        try: data=json.loads(body.decode() or '{}')
        except: return self._json(400,{'error':'bad json'})
        if p.startswith('/api/tasks/'):
            tid=p.rsplit('/',1)[-1]
            with LOCK:
                s=load(); t=next((x for x in s['tasks'] if x['id']==tid),None)
                if not t: return self._json(404,{'error':'task not found'})
                author=(data.get('author') or 'VIKI')[:40]
                for k in ('status','owner','link','note','title'):
                    if k in data and data[k] is not None:
                        t[k]=str(data[k])[:1000]
                if t.get('status') not in ('todo','doing','done','blocked'): t['status']='todo'
                t['updated_at']=now(); event(s,author,f"tarea {tid} → {t['status']}: {t['title'][:60]}"); save(s); return self._json(200,t)
        self._json(404,{'error':'not found'})
    def log_message(self,*a): pass

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--host',default='127.0.0.1'); ap.add_argument('--port',type=int,default=int(os.environ.get('PORT','8787'))); a=ap.parse_args()
    load(); print(f'VIKI Ops Panel on http://{a.host}:{a.port}'); ThreadingHTTPServer((a.host,a.port),H).serve_forever()
