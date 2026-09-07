#!/usr/bin/env python3
"""Initialize Athena 9.9.9 platform intent; probe only selected local CLI versions."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def normalize(value):
    if value == ['both'] or value == 'both':
        return ['cc', 'cx']
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value or any(item not in ['cc', 'cx'] for item in value):
        raise ValueError('platforms must contain cc/cx, or legacy both')
    return [kind for kind in ['cc', 'cx'] if kind in value]


def replace_field(text, name, value):
    line = name + ': ' + json.dumps(value, ensure_ascii=False)
    pattern = r'^' + re.escape(name) + r':[^\n]*$'
    if re.search(pattern, text, re.M):
        return re.sub(pattern, lambda match: line, text, count=1, flags=re.M)
    return text.replace('---\n', '---\n' + line + '\n', 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--platforms', choices=['cc', 'cx', 'both'], help='user intent; absence preserves existing selection')
    parser.add_argument('--template', type=Path, default=Path(__file__).resolve().parents[2] / 'pace/templates/_index.md')
    parser.add_argument('--refresh', action='store_true', help='rebuild selected CLI cache; does not authenticate')
    args = parser.parse_args()
    repo = args.repo.resolve()
    if subprocess.run(['git', '-C', str(repo), 'rev-parse', '--git-dir'], capture_output=True).returncode:
        parser.error('Athena requires a Git repository')
    state = repo / '.ai_state'
    index = state / '_index.md'
    text = index.read_text() if index.exists() else args.template.read_text()
    selected = args.platforms
    if selected is None and index.exists():
        match = re.search(r'^platforms_enabled:\s*(\[[^\n]*?\])', text, re.M)
        if match:
            selected = json.loads(match.group(1))
    if selected is None:
        selected = 'cc' if '.claude' in Path(__file__).parts else 'cx'
    selected = normalize(selected)
    cache_path = state / '.runtime/platform-capabilities.json'
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
            if not isinstance(cache, dict) or any(not isinstance(value, dict) for value in cache.values()):
                cache = {}
        except (ValueError, OSError):
            cache = {}  # Rebuildable capability cache is not project truth.
    capabilities = {}
    for kind in selected:
        executable = shutil.which('claude' if kind == 'cc' else 'codex')
        marker = None
        if executable:
            info = Path(executable).stat()
            marker = {'path': executable, 'mtime_ns': info.st_mtime_ns, 'size': info.st_size}
        previous = cache.get(kind)
        if previous and previous.get('executable') == marker and not args.refresh:
            capabilities[kind] = previous
            continue
        version, status = '', 'unavailable'
        if executable:
            try:
                result = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                status = 'unknown'
            else:
                if result.returncode == 0:
                    version, status = result.stdout.strip()[:160], 'available'
                else:
                    status = 'unknown'
        capabilities[kind] = {'version': version, 'status': status, 'executable': marker,
                              'checked_at': datetime.now(timezone.utc).isoformat(),
                              'native_capabilities': 'require current interface observation; version alone is insufficient'}
    updated = replace_field(text, 'platforms_enabled', selected)
    if not index.exists():
        # Template capability examples are not observations of the current native interface.
        updated = re.sub(r'^(\s+(?:cc|cx)_[A-Za-z0-9_]+:)\s*(?:true|false)([^\n]*)$',
                         lambda match: match.group(1) + ' false' + match.group(2), updated, flags=re.M)
    for kind in ['cc', 'cx']:
        if kind not in selected:
            updated = re.sub(r'^(\s+' + kind + r'_[A-Za-z0-9_]+:)\s*(?:true|false)([^\n]*)$',
                             lambda match: match.group(1) + ' false' + match.group(2), updated, flags=re.M)
        updated = replace_field(updated, kind + '_version', capabilities.get(kind, {}).get('version', ''))
    if not index.exists() or updated != text:
        atomic(index, updated)
    if capabilities != cache:
        atomic(cache_path, json.dumps(capabilities, indent=2) + '\n')
    for name in ['sprints', 'roadmap', 'architecture', 'requirements', 'compound']:
        (state / name).mkdir(exist_ok=True)
    # Local Git exclusion keeps the rebuildable cache out of commits without touching project policy.
    exclusion = Path(subprocess.check_output(['git', '-C', str(repo), 'rev-parse', '--git-path', 'info/exclude'], text=True).strip())
    if not exclusion.is_absolute():
        exclusion = repo / exclusion
    existing = exclusion.read_text() if exclusion.exists() else ''
    if '.ai_state/.runtime/' not in existing.splitlines():
        atomic(exclusion, existing.rstrip('\n') + '\n.ai_state/.runtime/\n')
    print(json.dumps({'platforms_enabled': selected, 'capabilities': {kind: record['status'] for kind, record in capabilities.items()},
                      'vm': 'not_probed; runtime doctor reports configuration and transport separately'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
