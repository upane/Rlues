"""Content bindings, collected only for validation commands and review boundaries.

No raw environment or secret values enter hashes. Runtime recipes opt in with
public scalar fields; external/remote assertions retain their own runner evidence.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from _index_io import write_atomic

FIELDS = ('source_sha256', 'design_sha256', 'environment_sha256')
PUBLIC_ENV = {'system', 'release', 'machine', 'os', 'arch', 'image', 'runtime', 'version', 'scenario', 'seed', 'recipe', 'required'}
VALIDATION = re.compile(r'\b(?:pytest|unittest|(?:npm|pnpm|yarn|bun)\s+(?:test|run\s+(?:test|build|lint|typecheck|check))|cargo\s+(?:test|build|check|clippy)|go\s+(?:test|build|vet)|mvn\s+(?:test|verify)|(?:eslint|ruff|tsc)\b|node\s+--check|git\s+diff\s+--check)\b')

def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def required(sprint: Path) -> bool:
    """Only the active 9.9.9+ sprint is upgraded, never historical reviews."""
    index = sprint.parents[1]/'_index.md'
    if not index.is_file():
        return False
    text = index.read_text()
    version = re.search(r'^version:\s*["\']?(\d+)\.(\d+)\.(\d+)',text,re.M)
    slug = re.search(r'^current_sprint_slug:\s*["\']?([A-Za-z0-9][A-Za-z0-9._-]*)',text,re.M)
    return bool(version and slug and tuple(map(int,version.groups())) >= (9,9,9) and slug.group(1) == sprint.name)

def digest(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()

def git(root: Path, *args: str) -> bytes:
    run = subprocess.run(['git', *args], cwd=root, capture_output=True, timeout=15)
    if run.returncode:
        raise ValueError('git input unavailable: ' + run.stderr.decode('utf-8', 'replace').strip())
    return run.stdout

def context(cwd: Path) -> tuple[Path, Path]:
    root = Path(git(Path(cwd), 'rev-parse', '--show-toplevel').decode().strip())
    text = (root/'.ai_state/_index.md').read_text()
    match = re.search(r'^current_sprint_slug:\s*["\']?([A-Za-z0-9][A-Za-z0-9._-]*)', text, re.M)
    if not match:
        raise ValueError('current sprint unavailable')
    return root, root/'.ai_state/sprints'/match.group(1)

def source_sha256(root: Path) -> str:
    names = sorted(set(n.decode('utf-8') for n in git(root, 'ls-files', '-z', '-c', '-o', '--exclude-standard').split(b'\0') if n))
    h = hashlib.sha256()
    for name in names:
        parts = Path(name).parts
        if parts[0] in {'.ai_state', '.runtime'}:
            continue
        if any(p.startswith('.env') or p.endswith(('.pem', '.key', '.p12')) or p.lower() in {'credentials', 'secrets'} for p in parts):
            continue
        target = root/name
        h.update(name.encode() + b'\0')
        if target.is_symlink():
            h.update(b'link\0' + os.readlink(target).encode())
        elif not target.exists():
            h.update(b'deleted')
        elif target.is_file():
            h.update((b'executable\0' if target.stat().st_mode & 0o111 else b'file\0') + target.read_bytes())
        else:
            raise ValueError('unsupported source directory/submodule: ' + name)
        h.update(b'\n')
    return h.hexdigest()

def environment(root: Path) -> dict:
    uname = os.uname()
    result = {'system': uname.sysname.lower(), 'release': uname.release, 'machine': uname.machine, 'recipe': []}
    for name in ('.ai_state/runtime-env.yaml', '.ai_state/conventions/runtime-env.yaml', '.ai_state/conventions/runtime-env.md'):
        file = root/name
        if not file.is_file():
            continue
        public = []
        for line in file.read_text().splitlines():
            match = re.match(r'^\s*([A-Za-z_]+):\s*(.*?)\s*$', line)
            if match and match.group(1) in PUBLIC_ENV:
                value = match.group(2)
                if re.search(r'://[^/\s]*@|(?i:token|password|secret|api.key)\s*[=:]', value):
                    raise ValueError('public environment field contains credential syntax')
                public.append([match.group(1), value])
        result['recipe'].append([name, public])
    return result

def snapshot(root: Path, sprint: Path) -> dict:
    return {'source_sha256': source_sha256(root), 'design_sha256': digest((sprint/'design.md').read_bytes()),
            'environment_sha256': digest(canonical(environment(root)))}

def command_of(payload) -> str:
    value = payload.get('tool_input') or {}
    return str(value.get('command') or value.get('cmd') or '')

def execution_cwd(payload) -> Path:
    tool_input = payload.get('tool_input') or {}
    return Path(tool_input.get('workdir') or payload.get('cwd') or Path.cwd())

def pre_path(root: Path, payload) -> Path:
    ident = payload.get('tool_use_id')
    if not isinstance(ident, str) or not ident:
        raise ValueError('native tool_use_id unavailable')
    return root/'.ai_state/.runtime/evidence-inputs'/(digest(ident) + '.json')

def capture_before(payload) -> None:
    if not VALIDATION.search(command_of(payload)):
        return
    if re.search(r'(?:^|[;&|]\s*)cd\s', command_of(payload)):
        raise ValueError('use the tool workdir for validation; shell directory changes are not bound')
    root, sprint = context(execution_cwd(payload))
    path = pre_path(root, payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, canonical(snapshot(root, sprint)))

def finish(payload, redacted_output: str) -> dict:
    try:
        root, sprint = context(execution_cwd(payload))
        path = pre_path(root, payload)
        before = json.loads(path.read_text())
        path.unlink()
        current = snapshot(root, sprint)
        if before != current:
            return {'binding_status': 'unverifiable'}
        output = sprint/'evidence'/(digest(payload['tool_use_id']) + '.txt')
        output.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(output, redacted_output)
        return {**current, 'binding_status': 'current', 'output_artifact': output.relative_to(sprint).as_posix(),
                'artifact_sha256': digest(output.read_bytes())}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'binding_status': 'unverifiable'}

def current_record(record: dict, root: Path, sprint: Path, live: dict | None = None) -> bool:
    if record.get('binding_status') != 'current':
        return False
    try:
        current = live or snapshot(root, sprint)
        target = (sprint/record['output_artifact']).resolve()
        if not target.is_relative_to(sprint.resolve()):
            return False
        return all(record.get(k) == current[k] for k in FIELDS) and digest(target.read_bytes()) == record.get('artifact_sha256')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return False
