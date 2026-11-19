"""Gera ZIP de entrega, sem ambientes, dependências, segredos ou dados de execução."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '.tools', '.venv', 'node_modules', '__pycache__', '.dart_tool',
             '.idea', '.gradle', '.runtime', 'build', 'dist', '.pytest_cache'}
SKIP_NAMES = {'.env', 'secrets.h', 'local.properties', '.flutter-plugins-dependencies',
              '.DS_Store', 'occurrences.json'}


def allowed(path):
    relative = path.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in relative.parts):
        return False
    if path.name in SKIP_NAMES or path.suffix in {'.log', '.pyc', '.iml'}:
        return False
    if relative.parts[:3] == ('modules', 'cnn', 'data'):
        return False
    if relative.parts[:2] == ('web', 'data'):
        return False
    return True


def main():
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    target = output / 'Territorio-Vivo-GS2026.2.zip'
    manifest = []
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        # Walk é podado para não percorrer milhares de arquivos de SDKs/venvs.
        import os
        for folder, directories, names in os.walk(ROOT):
            directories[:] = sorted(name for name in directories if name not in SKIP_DIRS
                                    and allowed(Path(folder) / name))
            for name in sorted(names):
                path = Path(folder) / name
                if not allowed(path):
                    continue
                contents = path.read_bytes()
                relative = path.relative_to(ROOT).as_posix()
                archive.writestr(f'Territorio-Vivo/{relative}', contents)
                manifest.append({'path': relative, 'bytes': len(contents),
                                 'sha256': hashlib.sha256(contents).hexdigest()})
        archive.writestr('Territorio-Vivo/ARQUIVOS.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(target) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f'ZIP inválido: {bad}')
    print(json.dumps({'archive': str(target), 'files': len(manifest), 'bytes': target.stat().st_size,
                      'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
