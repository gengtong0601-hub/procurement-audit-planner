#!/usr/bin/env python3
"""Package the handoff without credentials, local environments or review tokens."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'delivery/procurement-audit-planner-handoff.zip'
EXCLUDE_DIRS = {'.git', '.venv', '__pycache__', '.pytest_cache', 'runtime', 'delivery', 'node_modules', 'agent-memory'}


def include(path):
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    if path.name.startswith('.env') and path.name != '.env.example':
        return False
    if path.name in {'.DS_Store', 'settings.local.json'} or path.suffix in {'.pyc', '.pyo'}:
        return False
    if rel.parts[:2] == ('docs', 'reference') and (path.suffix == '.html' or path.name == 'data.zip'):
        return False
    return path.is_file()


if __name__ == '__main__':
    TARGET.parent.mkdir(exist_ok=True)
    files = sorted(p for p in ROOT.rglob('*') if include(p))
    with ZipFile(TARGET, 'w', ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path('procurement-audit-planner') / path.relative_to(ROOT))
    with ZipFile(TARGET) as archive:
        if archive.testzip() is not None:
            raise SystemExit('Archive integrity failed')
    print(f'{len(files)} files; {TARGET.stat().st_size:,} bytes; {TARGET.relative_to(ROOT)}')
