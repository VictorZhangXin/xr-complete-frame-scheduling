from pathlib import Path
import json,hashlib
from integrity import safe_relative
root=Path(__file__).resolve().parent
manifest=json.loads((root/'RELEASE.json').read_text(encoding='utf-8'))
for name,expected in manifest['files'].items():
    path=safe_relative(root,name)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Checksum mismatch: '+name)
print('Release verified:',len(manifest['files']),'files')
