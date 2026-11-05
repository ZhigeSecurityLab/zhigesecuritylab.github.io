"""Local, profile-scoped editor for the GitHub user garrisongys."""
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
import base64
import copy
import hashlib
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import threading
import webbrowser

import admin
from build import ROOT, OUT, MARKDOWN, build, validate
from media import store_avatar

OWNER = "garrisongys"
REPO = "ZhigeSecurityLab/zhigesecuritylab.github.io"
UI = ROOT / "faculty_editor"
CONFIG = ROOT / ".local/faculty-github-auth"
BASELINE = ROOT / ".local/faculty-baseline.json"
TOKEN = secrets.token_urlsafe(32)
AUTH_STATE = {"state": "idle"}
LOCK = threading.Lock()
FIELDS = ("name", "role", "url", "bio_markdown")


def gh(args, payload=None):
    binary = admin.publish.gh_path()
    if not binary:
        raise RuntimeError("请先安装 GitHub CLI。")
    env = dict(os.environ, GH_CONFIG_DIR=str(CONFIG), GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1")
    result = subprocess.run([binary] + args, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, cwd=ROOT, env=env, timeout=35)
    if result.returncode:
        if "404" in result.stderr:
            raise FileNotFoundError("GitHub 文件不存在")
        if "409" in result.stderr or "422" in result.stderr:
            raise RuntimeError("远程内容已变化，请重新同步后重试；本地资料已保留。")
        raise RuntimeError("GitHub 请求失败，请检查登录、仓库权限和网络。")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def connection():
    if not admin.publish.gh_path():
        return {"installed": False, "connected": False, "account": "", "login": dict(AUTH_STATE)}
    try:
        user = gh(["api", "user"])["login"]
        repo = gh(["api", "repos/" + REPO])
        return {"installed": True, "connected": user.lower() == OWNER and bool(repo.get("permissions", {}).get("push")),
                "account": user, "login": dict(AUTH_STATE)}
    except (RuntimeError, subprocess.TimeoutExpired):
        return {"installed": True, "connected": False, "account": "", "login": dict(AUTH_STATE)}


def login():
    if AUTH_STATE["state"] == "waiting":
        return dict(AUTH_STATE)
    if not admin.publish.gh_path():
        raise RuntimeError("请先安装 GitHub CLI。")
    AUTH_STATE.update(state="waiting", message="正在获取一次性验证码…", url="https://github.com/login/device")
    threading.Thread(target=_login, daemon=True).start()
    return dict(AUTH_STATE)


def _login():
    try:
        CONFIG.mkdir(parents=True, exist_ok=True)
        CONFIG.chmod(0o700)
        env = dict(os.environ, GH_CONFIG_DIR=str(CONFIG), GH_NO_UPDATE_NOTIFIER="1")
        if os.name != "nt":
            env["GH_BROWSER"] = "/usr/bin/true"
        process = subprocess.Popen([admin.publish.gh_path(), "auth", "login", "--web", "--hostname", "github.com",
                                    "--git-protocol", "https"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, cwd=ROOT, env=env)
        process.stdin.write("\n")
        process.stdin.flush()
        timer = threading.Timer(900, process.terminate)
        timer.start()
        try:
            for line in process.stdout:
                match = re.search(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b", line)
                if match:
                    AUTH_STATE.update(code=match.group(1), message="请用 garrisongys 在 GitHub 输入验证码并授权。")
            exit_code = process.wait()
        finally:
            timer.cancel()
        AUTH_STATE.pop("code", None)
        AUTH_STATE.update(state="success" if exit_code == 0 and connection()["connected"] else "error",
                          message="garrisongys 已连接。" if exit_code == 0 and connection()["connected"] else "账号或仓库写入权限不匹配，请检查后重试。")
    except Exception:
        AUTH_STATE.update(state="error", message="连接失败，请检查 GitHub CLI 和网络。")


def own_record(data, lang):
    matches = [person for person in data[lang]["people"] if person.get("github_username", "").lower() == OWNER]
    if len(matches) > 1 or (matches and matches[0]["category"] != "faculty"):
        raise ValueError("Faculty 资料归属设置异常")
    return matches[0] if matches else None


def profiles(data):
    return {lang: own_record(data, lang) or {"name": "", "role": "", "url": "", "bio_markdown": "", "avatar": ""}
            for lang in ("en", "zh")}


def merge(data, submitted):
    result = copy.deepcopy(data)
    if not isinstance(submitted, dict) or set(submitted) != {"en", "zh", "avatar"}:
        raise ValueError("资料格式无效")
    avatar = submitted["avatar"]
    for lang in ("en", "zh"):
        source = submitted[lang]
        if not isinstance(source, dict) or set(source) != set(FIELDS):
            raise ValueError("资料字段无效")
        record = own_record(result, lang)
        if record is None:
            record = {"category": "faculty", "github_username": OWNER}
            result[lang]["people"].append(record)
        for field in FIELDS:
            record[field] = source[field]
        record["avatar"] = avatar
    return result


def current_state():
    raw = admin.CONTENT.read_bytes()
    data = json.loads(raw)
    p = profiles(data)
    return {"profiles": {lang: {field: p[lang].get(field, "") for field in FIELDS} for lang in ("en", "zh")},
            "avatar": p["en"].get("avatar", "") or p["zh"].get("avatar", ""),
            "revision": admin.revision(raw), "token": TOKEN}


def profile_hash(data):
    return hashlib.sha256(json.dumps(profiles(data), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def baseline_hash():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    try:
        saved = json.loads(BASELINE.read_text())
        if saved.get("git_head") == head:
            return saved["profile_hash"]
    except (OSError, ValueError, KeyError):
        pass
    raw = subprocess.check_output(["git", "show", "HEAD:content/site.json"], cwd=ROOT)
    return profile_hash(json.loads(raw))


def blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def publish_profile():
    if not connection()["connected"]:
        raise RuntimeError("请先使用 garrisongys 连接 GitHub，并确认仓库写入权限。")
    local = json.loads(admin.CONTENT.read_bytes())
    local_profiles = profiles(local)
    if not local_profiles["en"].get("avatar") or local_profiles["en"].get("avatar") != local_profiles["zh"].get("avatar"):
        raise ValueError("请先保存中英文资料和共用头像。")
    endpoint = "repos/" + REPO + "/contents/content/site.json"
    remote_file = gh(["api", endpoint + "?ref=main"])
    remote = json.loads(base64.b64decode(remote_file["content"]))
    if profile_hash(remote) != baseline_hash():
        raise RuntimeError("线上 Faculty 资料已有变化，请先同步仓库后重试，避免覆盖他人的修改。")
    avatar = local_profiles["en"]["avatar"]
    image_raw = (ROOT / avatar).read_bytes()
    image_endpoint = "repos/" + REPO + "/contents/" + avatar
    try:
        existing = gh(["api", image_endpoint + "?ref=main"])
    except FileNotFoundError:
        existing = None
    if existing and existing["sha"] != blob_sha(image_raw):
        raise RuntimeError("线上已有同名但内容不同的头像，请重新上传。")
    if not existing:
        gh(["api", "--method", "PUT", image_endpoint, "--input", "-"],
           {"message": "Add garrisongys faculty photo", "content": base64.b64encode(image_raw).decode(), "branch": "main"})
    submitted = {"avatar": avatar}
    for lang in ("en", "zh"):
        submitted[lang] = {field: local_profiles[lang].get(field, "") for field in FIELDS}
    updated = merge(remote, submitted)
    raw = (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode()
    result = gh(["api", "--method", "PUT", endpoint, "--input", "-"],
                {"message": "Update garrisongys faculty profile", "content": base64.b64encode(raw).decode(),
                 "sha": remote_file["sha"], "branch": "main"})
    BASELINE.parent.mkdir(exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    BASELINE.write_text(json.dumps({"git_head": head, "profile_hash": profile_hash(updated)}))
    return {"commit": result["commit"]["sha"], "url": "https://github.com/" + REPO + "/commit/" + result["commit"]["sha"]}


class Handler(admin.Handler):
    server_version = "ZhigeFacultyEditor/1.0"

    def do_GET(self):
        if not self.trusted_host():
            return self.send(403, {"error": "只允许本机访问"})
        path = urlsplit(self.path).path
        if path == "/api/state":
            return self.send(200, current_state())
        if path == "/api/connection":
            return self.send(200, connection())
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
            return self.send(403, {"error": "请求校验失败"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4_000_000 or self.headers.get_content_type() != "application/json":
                return self.send(413, {"error": "请求格式或大小无效"})
            payload = json.loads(self.rfile.read(length))
            path = urlsplit(self.path).path
            if path == "/api/connect":
                return self.send(200, login())
            if path == "/api/avatar":
                return self.send(200, {"path": store_avatar(payload.get("data"))})
            if path == "/api/markdown":
                body = payload.get("markdown")
                if not isinstance(body, str) or len(body) > 100000:
                    raise ValueError("Markdown 最长 100000 字符")
                with LOCK:
                    return self.send(200, {"html": MARKDOWN.render(body)})
            if path == "/api/save":
                with LOCK:
                    original = admin.CONTENT.read_bytes()
                    if payload.get("revision") != admin.revision(original):
                        raise RuntimeError("本地文件已变化，请重新加载后编辑。")
                    merged = merge(json.loads(original), payload["profile"])
                    validate(merged)
                    admin.save(merged, payload["revision"])
                    return self.send(200, current_state())
            if path == "/api/publish":
                with LOCK:
                    if payload.get("revision") != admin.revision(admin.CONTENT.read_bytes()):
                        raise RuntimeError("资料已变化，请先重新加载。")
                    return self.send(200, publish_profile())
            return self.send(404, {"error": "接口不存在"})
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            return self.send(409, {"error": str(exc)})
        except Exception as exc:
            self.log_error("Faculty editor error: %r", exc)
            return self.send(500, {"error": "操作失败，请查看启动终端。"})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    build()
    url = f"http://127.0.0.1:{args.port}/"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("Faculty 资料维护：" + url, flush=True)
    if args.open:
        webbrowser.open(url)
    server.serve_forever()
