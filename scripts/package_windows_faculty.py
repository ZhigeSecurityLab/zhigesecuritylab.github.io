"""Build a portable editor using the signed, official Python Windows runtime."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/FacultyOfficial'
OUT.mkdir(parents=True,exist_ok=True)
url='https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
raw=urllib.request.urlopen(url,timeout=60).read()
assert hashlib.sha256(raw).hexdigest()=='4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'
import io
with zipfile.ZipFile(io.BytesIO(raw)) as z:z.extractall(OUT/'runtime')
subprocess.run([sys.executable,'-m','pip','install','--target',str(OUT/'runtime'),'-r',str(ROOT/'requirements.txt')],check=True)
for name in ('scripts','assets','content','faculty_editor','student_editor'):
    shutil.copytree(ROOT/name,OUT/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copy2(shutil.which('gh'),OUT/'gh.exe')
(OUT/'runtime/python312._pth').write_text('python312.zip\n.\n../scripts\n')
(OUT/'Start-Faculty-Editor.bat').write_text('@echo off\nchcp 65001 >nul\ncd /d "%~dp0"\nruntime\\python.exe scripts\\faculty.py --user garrisongys --branch main --port 8002 --open\nif errorlevel 1 pause\n')
shutil.copy2(ROOT/'portable/Faculty-README.txt',OUT/'Faculty-README.txt')
