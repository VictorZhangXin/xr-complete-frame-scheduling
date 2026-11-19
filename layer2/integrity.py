from pathlib import Path, PurePosixPath
import hashlib, json

def safe_relative(root, name):
    normalized=name.replace('\\','/')
    p=PurePosixPath(normalized)
    if p.is_absolute() or '..' in p.parts or ':' in normalized or not p.parts:
        raise ValueError('Unsafe manifest path: '+name)
    root=Path(root).resolve()
    result=root.joinpath(*p.parts).resolve()
    if not result.is_relative_to(root):raise ValueError('Escaping manifest path')
    return result

def hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(root).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}

def write_json(path, obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
