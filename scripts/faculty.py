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
import sys
import threading
import webbrowser
from urllib.request import Request, urlopen

import admin
from build import ROOT, OUT, MARKDOWN, build, validate
from media import store_avatar

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OWNER = "garrisongys"
BRANCH = "main"
REPO = "ZhigeSecurityLab/zhigesecuritylab.github.io"
UI = ROOT / "faculty_editor"
CONFIG = ROOT / ".local/faculty-github-auth"
BASELINE = ROOT / ".local/faculty-baseline.json"
TOKEN = secrets.token_urlsafe(32)
AUTH_STATE = {"state": "idle"}
LOCK = threading.Lock()
FIELDS = ("name", "role", "url", "bio_markdown")
DRAFT_AVATAR = "assets/people/draft-preview.jpg"
DRAFT_NAMES = {"en": "Faculty preview", "zh": "教师资料预览"}


def gh(args, payload=None):
    binary = gh_binary()
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


def gh_binary():
    bundled = ROOT / ("gh.exe" if os.name == "nt" else "gh")
    return str(bundled) if bundled.is_file() else admin.publish.gh_path()


def connection():
    if not gh_binary():
        return {"installed": False, "connected": False, "account": "", "login": dict(AUTH_STATE)}
    try:
        user = gh(["api", "user"])["login"]
        repo = gh(["api", "repos/" + REPO])
        return {"installed": True, "connected": user.lower() == OWNER.lower() and bool(repo.get("permissions", {}).get("push")),
                "account": user, "login": dict(AUTH_STATE)}
    except (RuntimeError, subprocess.TimeoutExpired):
        return {"installed": True, "connected": False, "account": "", "login": dict(AUTH_STATE)}


def login():
    if AUTH_STATE["state"] == "waiting":
        return dict(AUTH_STATE)
    if not gh_binary():
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
        process = subprocess.Popen([gh_binary(), "auth", "login", "--web", "--hostname", "github.com",
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
                    AUTH_STATE.update(code=match.group(1), message=f"请用 {OWNER} 在 GitHub 输入验证码并授权。")
            exit_code = process.wait()
        finally:
            timer.cancel()
        AUTH_STATE.pop("code", None)
        AUTH_STATE.update(state="success" if exit_code == 0 and connection()["connected"] else "error",
                          message=f"{OWNER} 已连接。" if exit_code == 0 and connection()["connected"] else "账号或仓库写入权限不匹配，请检查后重试。")
    except Exception:
        AUTH_STATE.update(state="error", message="连接失败，请检查 GitHub CLI 和网络。")


def own_record(data, lang):
    matches = [person for person in data[lang]["people"] if person.get("github_username", "").lower() == OWNER.lower()]
    if len(matches) > 1 or (matches and matches[0]["category"] != "faculty"):
        raise ValueError("Faculty 资料归属设置异常")
    return matches[0] if matches else None


def profiles(data):
    return {lang: own_record(data, lang) or {"name": "", "role": "", "url": "", "bio_markdown": "", "avatar": ""}
            for lang in ("en", "zh")}


def merge(data, submitted=None, recruitment=None):
    result = copy.deepcopy(data)
    if submitted is not None:
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
    if recruitment is not None:
        expected = {"enabled", "title", "body_markdown", "cta_label", "email_subject"}
        if not isinstance(recruitment, dict) or set(recruitment) != {"en", "zh"}:
            raise ValueError("Recruitment 格式无效")
        for lang in ("en", "zh"):
            if not isinstance(recruitment[lang], dict) or set(recruitment[lang]) != expected:
                raise ValueError("Recruitment 字段无效")
            result[lang]["recruitment"] = copy.deepcopy(recruitment[lang])
    return result


def preview_profile(submitted):
    """Fill required public-site fields in a local draft without claiming they are complete."""
    if submitted is None:
        return None
    draft = copy.deepcopy(submitted)
    if not draft.get("avatar"):
        target = ROOT / DRAFT_AVATAR
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "assets/logo.jpg", target)
        draft["avatar"] = DRAFT_AVATAR
    for lang in ("en", "zh"):
        if not draft[lang].get("name", "").strip():
            draft[lang]["name"] = DRAFT_NAMES[lang]
    return draft


def current_state():
    raw = admin.CONTENT.read_bytes()
    data = json.loads(raw)
    p = profiles(data)
    return {"profiles": {lang: {field: ("" if field == "name" and p[lang].get("name") == DRAFT_NAMES[lang]
                                        else p[lang].get(field, "")) for field in FIELDS} for lang in ("en", "zh")},
            "avatar": "" if p["en"].get("avatar") == DRAFT_AVATAR else (p["en"].get("avatar", "") or p["zh"].get("avatar", "")),
            "recruitment": {lang: data[lang]["recruitment"] for lang in ("en", "zh")},
            "owner": OWNER, "branch": BRANCH, "revision": admin.revision(raw), "token": TOKEN}


def profile_hash(data):
    return hashlib.sha256(json.dumps(profiles(data), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def recruitment_hash(data):
    return hashlib.sha256(json.dumps({lang: data[lang]["recruitment"] for lang in ("en", "zh")},
                                     sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def baseline_hash(scope):
    try:
        saved = json.loads(BASELINE.read_text())
        if saved.get("branch") == BRANCH:
            return saved[scope + "_hash"]
    except (OSError, ValueError, KeyError):
        pass
    try:
        raw = subprocess.check_output(["git", "show", "HEAD:content/site.json"], cwd=ROOT)
    except (OSError, subprocess.CalledProcessError):
        raise RuntimeError("尚未建立线上同步基线，请联网重新启动编辑器。")
    return (profile_hash if scope == "profile" else recruitment_hash)(json.loads(raw))


def save_baseline(data):
    BASELINE.parent.mkdir(exist_ok=True)
    BASELINE.write_text(json.dumps({"branch": BRANCH, "profile_hash": profile_hash(data),
                                    "recruitment_hash": recruitment_hash(data),
                                    "local_sha": admin.revision(admin.CONTENT.read_bytes())}))


def fetch_remote():
    endpoint = f"https://api.github.com/repos/{REPO}/contents/content/site.json?ref={BRANCH}"
    with urlopen(Request(endpoint, headers={"User-Agent": "Zhige-faculty-editor"}), timeout=20) as response:
        return json.loads(base64.b64decode(json.load(response)["content"]))


def sync_on_start():
    """Refresh a clean portable copy while preserving edits from a previous session."""
    try:
        saved = json.loads(BASELINE.read_text())
    except (OSError, ValueError):
        saved = {}
    local_raw = admin.CONTENT.read_bytes()
    if saved.get("branch") == BRANCH and saved.get("local_sha") != admin.revision(local_raw):
        print("检测到未发布的本地修改，保留当前资料。", flush=True)
        return
    try:
        remote = fetch_remote()
        for lang in ("en", "zh"):
            for person in remote[lang]["people"]:
                path = person.get("avatar", "")
                if not re.fullmatch(r"assets/people/[a-zA-Z0-9_-]+\.(?:jpg|png|webp)", path):
                    raise ValueError("线上成员头像路径无效")
                target = ROOT / path
                if not target.is_file():
                    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"
                    with urlopen(Request(url, headers={"User-Agent": "Zhige-faculty-editor"}), timeout=20) as response:
                        raw = response.read(2_500_001)
                    if len(raw) > 2_500_000:
                        raise ValueError("线上头像文件过大")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
        validate(remote)
        admin.CONTENT.write_text(json.dumps(remote, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save_baseline(remote)
        print(f"已同步 GitHub {BRANCH} 分支的最新内容。", flush=True)
    except Exception as exc:
        print(f"未能同步线上内容，使用本地副本：{exc}", flush=True)


def blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def publish_profile():
    if not connection()["connected"]:
        raise RuntimeError(f"请先使用 {OWNER} 连接 GitHub，并确认仓库写入权限。")
    local = json.loads(admin.CONTENT.read_bytes())
    local_profiles = profiles(local)
    scopes = {scope for scope, function in (("profile", profile_hash), ("recruitment", recruitment_hash))
              if function(local) != baseline_hash(scope)}
    endpoint = "repos/" + REPO + "/contents/content/site.json"
    remote_file = gh(["api", endpoint + "?ref=" + BRANCH])
    remote = json.loads(base64.b64decode(remote_file["content"]))
    if not scopes:
        return {"unchanged": True, "branch": BRANCH}
    for scope in scopes:
        function = profile_hash if scope == "profile" else recruitment_hash
        if function(remote) != baseline_hash(scope):
            raise RuntimeError(f"线上 {scope} 内容已有变化，请先同步后重试，避免覆盖他人的修改。")
    submitted = None
    if "profile" in scopes:
        if (not local_profiles["en"].get("avatar") or local_profiles["en"]["avatar"] == DRAFT_AVATAR
                or local_profiles["en"].get("avatar") != local_profiles["zh"].get("avatar")
                or any(local_profiles[lang].get("name") == DRAFT_NAMES[lang] for lang in ("en", "zh"))):
            raise ValueError("正式推送前，请填写中英文姓名并上传共用头像；本地草稿已保留。")
        avatar = local_profiles["en"]["avatar"]
        image_raw = (ROOT / avatar).read_bytes()
        image_endpoint = "repos/" + REPO + "/contents/" + avatar
        try:
            existing = gh(["api", image_endpoint + "?ref=" + BRANCH])
        except FileNotFoundError:
            existing = None
        if existing and existing["sha"] != blob_sha(image_raw):
            raise RuntimeError("线上已有同名但内容不同的头像，请重新上传。")
        if not existing:
            gh(["api", "--method", "PUT", image_endpoint, "--input", "-"],
               {"message": f"Add {OWNER} faculty photo", "content": base64.b64encode(image_raw).decode(), "branch": BRANCH})
        submitted = {"avatar": avatar}
        for lang in ("en", "zh"):
            submitted[lang] = {field: local_profiles[lang].get(field, "") for field in FIELDS}
    recruitment = ({lang: local[lang]["recruitment"] for lang in ("en", "zh")}
                   if "recruitment" in scopes else None)
    updated = merge(remote, submitted, recruitment)
    raw = (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode()
    result = gh(["api", "--method", "PUT", endpoint, "--input", "-"],
                {"message": f"Update {OWNER} faculty and recruitment content", "content": base64.b64encode(raw).decode(),
                 "sha": remote_file["sha"], "branch": BRANCH})
    save_baseline(updated)
    return {"commit": result["commit"]["sha"], "branch": BRANCH,
            "url": "https://github.com/" + REPO + "/commit/" + result["commit"]["sha"]}


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
                    merged = merge(json.loads(original), preview_profile(payload.get("profile")), payload.get("recruitment"))
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
    parser.add_argument("--user", default="garrisongys", choices=("garrisongys", "zhengfeiLian"))
    parser.add_argument("--branch", default="main", choices=("main", "faculty-editor-test"))
    args = parser.parse_args()
    OWNER = args.user
    BRANCH = args.branch
    if (OWNER, BRANCH) not in {("garrisongys", "main"), ("zhengfeiLian", "faculty-editor-test")}:
        parser.error("账号与目标分支不匹配")
    CONFIG = ROOT / (".local/faculty-github-auth-" + OWNER.lower())
    BASELINE = ROOT / (".local/faculty-baseline-" + OWNER.lower() + "-" + BRANCH + ".json")
    sync_on_start()
    build()
    url = f"http://127.0.0.1:{args.port}/"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("Faculty 资料维护：" + url, flush=True)
    if args.open:
        webbrowser.open(url)
    server.serve_forever()
