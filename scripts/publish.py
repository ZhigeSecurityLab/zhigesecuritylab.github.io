"""Publish the editor's content file using GitHub's optimistic SHA check.
Credentials are owned by GitHub CLI; no token is sent to the browser or repository.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from urllib.request import Request, urlopen

from build import ROOT

REPO = 'ZhigeSecurityLab/zhigesecuritylab.github.io'
LOCAL = ROOT / '.local'
STATE_FILE = LOCAL / 'publish-state.json'
MUTEX = threading.Lock()
JOB = {'state': 'idle', 'message': '尚未发布。'}
LOGIN = {'state': 'idle'}
AUTH = {'checked': float('-inf'), 'connected': False, 'account': ''}
LAST_CHECK = float('-inf')


def gh_path():
    local = LOCAL / 'bin/gh'
    return str(local) if local.is_file() else shutil.which('gh')


def gh(args, payload=None, timeout=30):
    binary = gh_path()
    if not binary:
        raise RuntimeError('未安装 GitHub CLI。请按维护指南安装后重新检查连接。')
    env = dict(os.environ, GH_PROMPT_DISABLED='1', GH_NO_UPDATE_NOTIFIER='1')
    result = subprocess.run([binary] + args, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, cwd=ROOT, env=env, timeout=timeout)
    if result.returncode:
        if '409' in result.stderr or '422' in result.stderr:
            raise RuntimeError('GitHub 内容已变化，请先同步远程内容后重试；本地修改已保留。')
        raise RuntimeError('GitHub 请求失败，请检查登录、仓库写入权限或网络后重试；本地修改已保留。')
    return json.loads(result.stdout) if result.stdout.strip() else {}


def connection(force=False):
    if force or time.monotonic() - AUTH['checked'] > 30:
        AUTH.update(checked=time.monotonic(), connected=False, account='')
        if gh_path():
            try:
                user = gh(['api', 'user'], timeout=10)
                repo = gh(['api', 'repos/' + REPO], timeout=10)
                AUTH.update(connected=bool(repo.get('permissions', {}).get('push')), account=user['login'])
            except (RuntimeError, subprocess.TimeoutExpired):
                pass
    return {'installed': bool(gh_path()), 'connected': AUTH['connected'], 'account': AUTH['account'],
            'repository': REPO, 'login': dict(LOGIN)}


def begin_login():
    with MUTEX:
        if JOB['state'] == 'publishing':
            raise RuntimeError('正在发布，请稍后连接。')
        if LOGIN['state'] == 'waiting':
            return dict(LOGIN)
        if not gh_path():
            raise RuntimeError('请先安装 GitHub CLI，详见维护指南。')
        LOGIN.clear()
        LOGIN.update(state='waiting', message='正在获取 GitHub 设备验证码…', url='https://github.com/login/device')
        threading.Thread(target=_login, daemon=True).start()
        return dict(LOGIN)


def _login():
    try:
        env = dict(os.environ, GH_BROWSER='/usr/bin/true', GH_NO_UPDATE_NOTIFIER='1')
        process = subprocess.Popen([gh_path(), 'auth', 'login', '--web', '--hostname', 'github.com',
                                    '--git-protocol', 'https'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, env=env, cwd=ROOT)
        process.stdin.write('\n')
        process.stdin.flush()
        timer = threading.Timer(900, process.terminate)
        timer.start()
        try:
            for line in process.stdout:
                match = re.search(r'\b([A-Z0-9]{4}-[A-Z0-9]{4})\b', line)
                if match:
                    LOGIN.update(code=match.group(1), message='请打开 GitHub 授权页面，输入此验证码并完成授权。')
            code = process.wait()
        finally:
            timer.cancel()
        AUTH['checked'] = float('-inf')
        if code == 0:
            LOGIN.update(state='success', message='GitHub 已连接，可发布到网站。')
        else:
            LOGIN.update(state='error', message='连接未完成或已过期，请重新连接。')
        LOGIN.pop('code', None)
    except Exception:
        LOGIN.update(state='error', message='无法启动连接，请检查 GitHub CLI 与网络。')


def load_record():
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_record(record):
    LOCAL.mkdir(exist_ok=True)
    tmp = STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(record), encoding='utf-8')
    tmp.chmod(0o600)
    os.replace(tmp, STATE_FILE)


def blob_sha(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def base_sha():
    saved = load_record().get('content_sha')
    if saved:
        return saved
    return subprocess.check_output(['git', 'rev-parse', 'HEAD:content/site.json'], cwd=ROOT, text=True).strip()


def begin_publish(raw):
    with MUTEX:
        if JOB['state'] in ('publishing', 'submitted'):
            raise RuntimeError('已有发布正在进行，请等待完成。')
        if LOGIN['state'] == 'waiting':
            raise RuntimeError('请先完成 GitHub 连接。')
        JOB.clear()
        JOB.update(state='publishing', message='正在检查远程版本并提交到 GitHub…')
        threading.Thread(target=_publish, args=(raw,), daemon=True).start()
        return dict(JOB)


def _publish(raw):
    try:
        endpoint = 'repos/' + REPO + '/contents/content/site.json'
        remote = gh(['api', endpoint + '?ref=main'])
        local_sha = blob_sha(raw)
        if remote['sha'] == local_sha:
            # An identical file needs no new commit; track the actual current main SHA.
            head = gh(['api', 'repos/' + REPO + '/commits/main'])['sha']
            previous = load_record()
            if previous.get('state') == 'deploy_error' and previous.get('commit') == head and previous.get('run_id'):
                gh(['api', '--method', 'POST', 'repos/' + REPO + '/actions/runs/' + str(previous['run_id']) + '/rerun'])
        else:
            if remote['sha'] != base_sha():
                raise RuntimeError('GitHub 上的内容已由其他人更新。请先同步后再发布，防止覆盖；本地修改已保留。')
            result = gh(['api', '--method', 'PUT', endpoint, '--input', '-'], {
                'message': 'Update lab content and appearance from maintenance dashboard',
                'content': base64.b64encode(raw).decode(), 'sha': remote['sha'], 'branch': 'main'})
            head = result['commit']['sha']
        record = {'content_sha': local_sha, 'commit': head, 'state': 'submitted',
                  'message': '已提交 GitHub，正在等待网站自动部署…', 'revision': hashlib.sha256(raw).hexdigest(),
                  'commit_url': 'https://github.com/' + REPO + '/commit/' + head}
        save_record(record)
        JOB.update(record)
    except Exception as exc:
        message = str(exc) if isinstance(exc, RuntimeError) else '发布失败，请检查网络后重试；本地保存未受影响。'
        JOB.update(state='error', message=message)


def deployment():
    global LAST_CHECK
    if JOB['state'] == 'idle':
        JOB.update(load_record())
    if JOB['state'] == 'submitted' and time.monotonic() - LAST_CHECK > 10:
        LAST_CHECK = time.monotonic()
        try:
            url = 'https://api.github.com/repos/' + REPO + '/actions/runs?head_sha=' + JOB['commit'] + '&event=push&per_page=20'
            response = json.load(urlopen(Request(url, headers={'User-Agent': 'Zhige-local-maintenance'}), timeout=10))
            runs = [r for r in response['workflow_runs'] if r['path'] == '.github/workflows/pages.yml']
            if runs:
                run = max(runs, key=lambda r: r['id'])
                JOB['run_url'] = run['html_url']
                JOB['run_id'] = run['id']
                if run['status'] == 'completed':
                    success = run['conclusion'] == 'success'
                    JOB.update(state='success' if success else 'deploy_error',
                               message='网站已更新，可以打开正式网站查看。' if success else '内容已提交，但部署未成功。请查看 GitHub Actions；修复后可重新发布。')
                else:
                    JOB['message'] = '内容已提交，GitHub 正在构建和部署网站…'
                save_record(dict(JOB))
        except (OSError, ValueError, KeyError):
            JOB['message'] = '内容已提交，暂时无法获取部署状态，可打开 GitHub Actions 查看。'
    return dict(JOB)
