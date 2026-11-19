"""Build a compact, self-contained release without environment/render caches."""
from pathlib import Path
import hashlib,json,zipfile,difflib
ROOT=Path(__file__).resolve().parent
for name,old in [('simulate.py','simulate.py'),('study.py','v2/study.py'),('analyze_study.py','v2/analyze_study.py')]:
    before=(ROOT/'baseline/xr_importance'/old).read_text(encoding='utf-8').splitlines(keepends=True)
    after=(ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True)
    mode='w' if name=='simulate.py' else 'a'
    with (ROOT/'review/code_changes.diff').open(mode,encoding='utf-8') as f:f.writelines(difflib.unified_diff(before,after,fromfile='uploaded/'+old,tofile='v3/'+name))
files=[]
for p in ROOT.rglob('*'):
    rel=p.relative_to(ROOT)
    if not p.is_file() or any(x in rel.parts for x in ('.deps','.venv','__pycache__','.mplconfig','qa','deliverables')) or p.suffix in ('.zip','.pyc') or p.name=='RELEASE.json':continue
    files.append(p)
release={'version':'v3.2','files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}}
(ROOT/'RELEASE.json').write_text(json.dumps(release,ensure_ascii=False,indent=2),encoding='utf-8')
dest=ROOT/'deliverables';dest.mkdir(exist_ok=True)
archive=dest/'XR_wireless_communication_project_v3_2.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[ROOT/'RELEASE.json']:z.write(p,'v3_2/'+p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:raise ValueError('Archive CRC failed')
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(files)+1}))
