"""Local visual editor. Start with .venv/bin/python scripts/admin.py."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, unquote
from datetime import datetime, timezone
import argparse
import hashlib
import json
import mimetypes
import os
import secrets
import shutil
import tempfile
import threading
import webbrowser
from urllib.request import urlopen

from build import ROOT, OUT, MARKDOWN, build, validate

CONTENT = ROOT / "content/site.json"
LOCAL = ROOT / ".local"
BACKUPS = LOCAL / "backups"
UI = ROOT / "admin"
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Lock()


def revision(raw):
    return hashlib.sha256(raw).hexdigest()


def state():
    raw = CONTENT.read_bytes()
    return {"data": json.loads(raw), "revision": revision(raw), "token": TOKEN,
            "backups": sorted((p.name for p in BACKUPS.glob("*.json")), reverse=True)[:50]}


def save(data, expected):
    with LOCK:
        before = CONTENT.read_bytes()
        if expected != revision(before):
            raise RuntimeError("内容已被其他窗口或文件编辑器修改。请先导出未保存内容，再重新加载后台。")
        validate(data)
        LOCAL.mkdir(exist_ok=True)
        BACKUPS.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="build-", dir=LOCAL) as temp:
            temp = Path(temp)
            built = temp / "site"
            build(data, built)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            (BACKUPS / f"{stamp}.json").write_bytes(before)
            candidate = temp / "site.json"
            candidate.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            old = temp / "previous-site"
            if OUT.exists():
                os.replace(OUT, old)
            try:
                os.replace(built, OUT)
                os.replace(candidate, CONTENT)
            except Exception:
                if OUT.exists():
                    shutil.rmtree(OUT)
                if old.exists():
                    os.replace(old, OUT)
                raise
        return state()


class Handler(BaseHTTPRequestHandler):
    server_version = "ZhigeEditor/1.0"

    def send(self, status, body, mime="application/json; charset=utf-8"):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https: http: data:; object-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def trusted_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.trusted_host():
            return self.send(403, {"error": "只允许本机访问维护后台"})
        path = urlsplit(self.path).path
        if path == "/api/state":
            return self.send(200, state())
        if path.startswith("/preview/"):
            root = OUT
            name = unquote(path[len("/preview/"):]) or "index.html"
        elif path.startswith("/assets/"):
            root = OUT
            name = unquote(path.lstrip("/"))
        else:
            root = UI
            name = unquote(path.lstrip("/")) or "index.html"
        target = (root / name).resolve()
        if root.resolve() not in target.parents:
            return self.send(403, {"error": "无效路径"})
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            return self.send(404, {"error": "文件不存在"})
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if mime.startswith("text/"):
            mime += "; charset=utf-8"
        return self.send(200, target.read_bytes(), mime)

    def do_POST(self):
        origin = self.headers.get("Origin")
        allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        if not self.trusted_host() or (origin is not None and origin not in allowed) or not secrets.compare_digest(self.headers.get("X-Editor-Token", ""), TOKEN):
            return self.send(403, {"error": "请求校验失败，请刷新维护后台"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4_000_000:
                return self.send(413, {"error": "内容为空或超过 4 MB"})
            if self.headers.get_content_type() != "application/json":
                return self.send(415, {"error": "需要 JSON 请求"})
            payload = json.loads(self.rfile.read(length))
            path = urlsplit(self.path).path
            if path == "/api/markdown":
                text = payload["markdown"]
                if not isinstance(text, str) or len(text) > 100000:
                    raise ValueError("Markdown 正文最长 100000 字符")
                # MarkdownIt holds parser state while rendering; serialize across threads.
                with LOCK:
                    html = MARKDOWN.render(text)
                return self.send(200, {"html": html})
            if path == "/api/save":
                return self.send(200, save(payload["data"], payload["revision"]))
            if path == "/api/restore":
                name = payload["backup"]
                if name not in {p.name for p in BACKUPS.glob("*.json")}:
                    raise ValueError("备份不存在")
                return self.send(200, save(json.loads((BACKUPS / name).read_bytes()), payload["revision"]))
            return self.send(404, {"error": "接口不存在"})
        except RuntimeError as exc:
            return self.send(409, {"error": str(exc)})
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            return self.send(400, {"error": f"保存失败：{exc}"})
        except Exception as exc:
            self.log_error("Editor error: %r", exc)
            return self.send(500, {"error": "操作失败，文件未保存。请查看启动终端。"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="止戈实验室本地维护后台")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--open", action="store_true", help="打开浏览器；已有后台时复用")
    args = parser.parse_args()
    editor_url = f"http://127.0.0.1:{args.port}/"
    if args.open:
        try:
            with urlopen(editor_url + "api/state", timeout=1) as response:
                existing = json.load(response)
            if all(key in existing for key in ("data", "revision", "token", "backups")):
                webbrowser.open(editor_url)
                raise SystemExit(0)
        except (OSError, ValueError):
            pass
    build()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"维护后台：http://127.0.0.1:{args.port}/", flush=True)
    print("保存会更新本地内容及预览；不会自动提交或推送 GitHub。", flush=True)
    if args.open:
        webbrowser.open(editor_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
