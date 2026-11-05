from __future__ import annotations

import json
import os
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = Path(os.environ.get("VIKI_HUB_DATA", str(ROOT.parent / "data" / "state.json"))).resolve()
HOST = os.environ.get("VIKI_HUB_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT") or os.environ.get("VIKI_HUB_PORT") or "8787")

LOCK = threading.Lock()
STATUSES = {"todo": "pendiente", "doing": "en progreso", "done": "hecho", "blocked": "bloqueado"}


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def default_state() -> dict:
    return {
        "meta": {"name": "VIKI Team Hub", "version": 1},
        "messages": [],
        "tasks": [],
        "events": [],
        "online": {},
    }


def load_state() -> dict:
    if not DATA.exists():
        s = default_state()
        save_state(s)
        return s
    with DATA.open("r", encoding="utf-8") as f:
        s = json.load(f)
    s.setdefault("messages", [])
    s.setdefault("tasks", [])
    s.setdefault("events", [])
    s.setdefault("online", {})
    s.setdefault("meta", {"name": "VIKI Team Hub", "version": 1})
    return s


def save_state(s: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA.with_suffix(DATA.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA)


def add_event(s: dict, who: str, what: str) -> None:
    s["events"].insert(0, {"id": uuid.uuid4().hex[:10], "at": now(), "who": who[:40], "what": what[:300]})
    s["events"] = s["events"][:300]


def touch_online(s: dict, who: str) -> None:
    if not who:
        return
    s["online"][who[:40]] = now()
    # keep last 50
    if len(s["online"]) > 50:
        items = sorted(s["online"].items(), key=lambda kv: kv[1], reverse=True)[:50]
        s["online"] = dict(items)


class Handler(BaseHTTPRequestHandler):
    server_version = "VikiTeamHub/1.0"

    def log_message(self, fmt, *args):
        return

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()

    def do_GET(self):
        p = unquote(urlparse(self.path).path)
        if p == "/api/state":
            with LOCK:
                s = load_state()
                who = (self.headers.get("X-Viki-Author") or "").strip()
                if who:
                    touch_online(s, who)
                    save_state(s)
                self._json(200, s)
            return
        if p == "/api/health":
            self._json(200, {"ok": True, "at": now(), "port": PORT})
            return
        if p in ("/", "/index.html"):
            target = STATIC / "index.html"
        else:
            rel = p.lstrip("/")
            target = (STATIC / rel).resolve()
            if STATIC.resolve() not in target.parents and target != STATIC.resolve():
                self._json(403, {"error": "forbidden"})
                return
        if not target.exists() or not target.is_file():
            self._json(404, {"error": "not found"})
            return
        ctype = "text/plain; charset=utf-8"
        if target.suffix == ".html": ctype = "text/html; charset=utf-8"
        elif target.suffix == ".css": ctype = "text/css; charset=utf-8"
        elif target.suffix == ".js": ctype = "application/javascript; charset=utf-8"
        elif target.suffix == ".json": ctype = "application/json; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    def do_POST(self):
        p = unquote(urlparse(self.path).path)
        data = self._read_json()
        with LOCK:
            s = load_state()
            author = str(data.get("author") or self.headers.get("X-Viki-Author") or "VIKI")[:40]
            touch_online(s, author)
            if p == "/api/messages":
                text = str(data.get("text") or "").strip()
                if not text:
                    self._json(400, {"error": "text required"})
                    return
                msg = {
                    "id": uuid.uuid4().hex[:10],
                    "at": now(),
                    "author": author,
                    "text": text[:4000],
                    "kind": str(data.get("kind") or "chat")[:20],
                    "taskId": str(data.get("taskId") or "")[:20] or None,
                }
                s["messages"].append(msg)
                s["messages"] = s["messages"][-800]
                add_event(s, author, f"mensaje: {text[:90]}")
                save_state(s)
                self._json(201, msg)
                return
            if p == "/api/tasks":
                title = str(data.get("title") or "").strip()
                if not title:
                    self._json(400, {"error": "title required"})
                    return
                status = str(data.get("status") or "todo")
                if status not in STATUSES:
                    status = "todo"
                task = {
                    "id": uuid.uuid4().hex[:10],
                    "title": title[:200],
                    "owner": str(data.get("owner") or "OpenCode")[:40],
                    "status": status,
                    "link": str(data.get("link") or "")[:600],
                    "note": str(data.get("note") or "")[:1500],
                    "created_at": now(),
                    "updated_at": now(),
                    "updated_by": author,
                }
                s["tasks"].insert(0, task)
                add_event(s, author, f"tarea creada: {task['title']} [{status}]")
                save_state(s)
                self._json(201, task)
                return
            if p == "/api/ping":
                save_state(s)
                self._json(200, {"ok": True, "author": author, "at": now()})
                return
        self._json(404, {"error": "not found"})

    def do_PATCH(self):
        p = unquote(urlparse(self.path).path)
        data = self._read_json()
        if not p.startswith("/api/tasks/"):
            self._json(404, {"error": "not found"})
            return
        tid = p.rsplit("/", 1)[-1]
        with LOCK:
            s = load_state()
            author = str(data.get("author") or self.headers.get("X-Viki-Author") or "VIKI")[:40]
            touch_online(s, author)
            task = next((t for t in s["tasks"] if t["id"] == tid), None)
            if not task:
                self._json(404, {"error": "task not found"})
                return
            for k in ("title", "owner", "link", "note"):
                if k in data and data[k] is not None:
                    task[k] = str(data[k])[:1500]
            if "status" in data and data["status"] in STATUSES:
                task["status"] = data["status"]
            task["updated_at"] = now()
            task["updated_by"] = author
            add_event(s, author, f"tarea {tid} → {task['status']}: {task['title'][:70]}")
            save_state(s)
            self._json(200, task)

    def do_DELETE(self):
        p = unquote(urlparse(self.path).path)
        if not p.startswith("/api/tasks/"):
            self._json(404, {"error": "not found"})
            return
        tid = p.rsplit("/", 1)[-1]
        with LOCK:
            s = load_state()
            before = len(s["tasks"])
            s["tasks"] = [t for t in s["tasks"] if t["id"] != tid]
            if len(s["tasks"]) == before:
                self._json(404, {"error": "task not found"})
                return
            add_event(s, "VIKI", f"tarea eliminada: {tid}")
            save_state(s)
            self._json(200, {"ok": True})


def main() -> None:
    with LOCK:
        load_state()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"VIKI Team Hub running at http://{HOST}:{PORT}")
    print(f"Data: {DATA}")
    server.serve_forever()


if __name__ == "__main__":
    main()
