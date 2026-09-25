"""Explicit read fallback for legacy assets; every new output belongs to this checkout.

No junctions, filesystem interception or asset copies. Configuration is local and
ignored by Git. Historical asset paths remain valid while F is connected.
"""
from pathlib import Path
import json
import os

ROOT = Path(__file__).resolve().parents[1]
_file = ROOT / 'workspace.local.json'
CONFIG = json.loads(_file.read_text(encoding='utf-8')) if _file.is_file() else {}
LEGACY_ROOT = Path(CONFIG['legacy_asset_root']).resolve() if CONFIG.get('legacy_asset_root') else None


def relative_path(value):
    path = Path(value)
    if path.is_absolute():
        for base in (ROOT, LEGACY_ROOT):
            if base and path.is_relative_to(base):
                path = path.relative_to(base)
                break
        else:
            raise ValueError(f'Path is outside configured project roots: {path}')
    if '..' in path.parts:
        raise ValueError(f'Parent traversal is not a project path: {path}')
    return path


def read_path(value):
    """Resolve one input file: prefer current checkout, then legacy assets.

    Apply at the file boundary, not to a directory that may exist in both roots.
    Missing inputs are errors; callers must never use this helper for writing.
    """
    relative = relative_path(value)
    explicit = Path(value)
    if explicit.is_absolute() and explicit.exists():
        if not any(base and explicit.resolve().is_relative_to(base.resolve()) for base in (ROOT, LEGACY_ROOT)):
            raise ValueError(f'Input link escapes configured project roots: {explicit}')
        return explicit
    for base in (ROOT, LEGACY_ROOT):
        if base:
            path = base / relative
            if path.exists():
                if not path.resolve().is_relative_to(base.resolve()):
                    raise ValueError(f'Input link escapes configured project root: {path}')
                return path
    raise FileNotFoundError(f'Missing project input: {relative}')


def write_path(value):
    """New output under the active checkout, even for a legacy absolute argument."""
    path = ROOT / relative_path(value)
    if not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError(f'Output escapes active workspace: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def validate_native(value):
    path = Path(value).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != '.blend' or not any(
        base and path.is_relative_to((base / 'native').resolve())
        for base in (ROOT, LEGACY_ROOT)
    ):
        raise ValueError(f'Not a native checkpoint in a configured project: {path}')
    return path


def executable(key):
    path = Path(CONFIG[key]).resolve(strict=True)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def configure_environment():
    """Keep bytecode, caches and temporary writes out of legacy installations."""
    temp = ROOT / 'runtime/tmp'
    temp.mkdir(parents=True, exist_ok=True)
    os.environ.update(ZURICH_WORKSPACE=str(ROOT), TMP=str(temp), TEMP=str(temp),
                      PYTHONDONTWRITEBYTECODE='1')
