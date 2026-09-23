"""Copy a quiescent project serially, verify SHA256, and retain the source.

This utility never deletes the source or switches runtime pointers. Reruns verify
existing destination files before skipping them. Native reopening and path repair
are separate migration gates. Do not edit either tree while it runs.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--journal', type=Path, required=True)
    args = parser.parse_args()
    src = args.source.resolve(strict=True)
    dst = args.destination.resolve()
    journal = args.journal.resolve()
    if src == dst or src in dst.parents or dst in src.parents:
        raise ValueError('Source and destination must be independent trees')
    if journal == src or src in journal.parents or journal == dst or dst in journal.parents:
        raise ValueError('Journal must be outside both copied trees')
    journal.mkdir(parents=True, exist_ok=True)
    dst.mkdir(parents=True, exist_ok=True)
    inventory = []
    directories = []
    for base, folders, names in os.walk(src, followlinks=False):
        base = Path(base)
        directories.append(base.relative_to(src).as_posix())
        for name in folders + names:
            path = base / name
            st = path.lstat()
            if getattr(st, 'st_file_attributes', 0) & 1024 or path.is_symlink():
                raise ValueError(f'Reparse point requires explicit handling: {path}')
            if path.is_file():
                inventory.append({'path': path.relative_to(src).as_posix(),
                                  'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns})
    def priority(item):
        name = item['path']
        if name == 'native/G1_019r2_limmat_clearance_working.blend':
            return (0, name)
        if name.startswith('runtime/tmp/'):
            return (3, name)
        if name.startswith(('native/', 'web/assets/')):
            return (2, name)
        return (1, name)
    inventory.sort(key=priority)
    total_bytes = sum(item['bytes'] for item in inventory)
    snapshot = {'source': str(src), 'destination': str(dst), 'files': inventory,
                'directories': directories, 'total_bytes': total_bytes,
                'source_retained': True}
    (journal / 'copy_inventory.json').write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
    for rel in directories:
        (dst / rel).mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    state = {'source': str(src), 'destination': str(dst), 'source_retained': True,
             'verified_files': 0, 'verified_bytes': 0, 'total_files': len(inventory),
             'total_bytes': total_bytes, 'current_file': None, 'current_bytes': 0,
             'phase': 'copying', 'started_local': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    last_report = 0
    def report(force=False):
        nonlocal last_report
        now = time.monotonic()
        if not force and now - last_report < 30:
            return
        state['elapsed_seconds'] = round(now - started, 2)
        state['updated_local'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        (journal / 'progress.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
        print(json.dumps(state), flush=True)
        last_report = now
    report(True)
    try:
        with (journal / 'verified_files.jsonl').open('w', encoding='utf-8') as receipts:
            for item in inventory:
                rel = item['path']
                source = src / rel
                target = dst / rel
                if not target.resolve().is_relative_to(dst):
                    raise ValueError(f'Destination escapes root: {rel}')
                st = source.stat()
                if (st.st_size, st.st_mtime_ns) != (item['bytes'], item['mtime_ns']):
                    raise RuntimeError(f'Source changed after inventory: {rel}')
                state.update(current_file=rel, current_bytes=0, phase='copying')
                before_hash = None
                skipped = False
                if target.is_file() and target.stat().st_size == item['bytes']:
                    state['phase'] = 'checking_existing'
                    report()
                    before_hash = digest(source)
                    skipped = before_hash == digest(target)
                if not skipped:
                    temp = target.with_name(target.name + '.zurich-transfer-part')
                    if temp.is_symlink() or (temp.exists() and getattr(temp.lstat(), 'st_file_attributes', 0) & 1024):
                        raise ValueError(f'Unsafe staging path: {temp}')
                    h = hashlib.sha256()
                    state['phase'] = 'copying'
                    with source.open('rb') as reader, temp.open('wb') as writer:
                        while block := reader.read(8 * 1024 * 1024):
                            writer.write(block)
                            h.update(block)
                            state['current_bytes'] += len(block)
                            report()
                        writer.flush()
                        state['phase'] = 'flushing'
                        report()
                        os.fsync(writer.fileno())
                    before_hash = h.hexdigest()
                    state['phase'] = 'verifying_destination'
                    report()
                    if temp.stat().st_size != item['bytes'] or digest(temp) != before_hash:
                        raise RuntimeError(f'Destination checksum mismatch: {rel}')
                    os.utime(temp, ns=(st.st_atime_ns, st.st_mtime_ns))
                    os.replace(temp, target)
                after = source.stat()
                if (after.st_size, after.st_mtime_ns) != (item['bytes'], item['mtime_ns']):
                    raise RuntimeError(f'Source modified during copy: {rel}')
                receipts.write(json.dumps({'path': rel, 'bytes': item['bytes'],
                                           'sha256': before_hash, 'existing_verified': skipped}) + '\n')
                receipts.flush()
                state['verified_files'] += 1
                state['verified_bytes'] += item['bytes']
                report()
        actual_paths = {p.relative_to(src).as_posix() for p in src.rglob('*') if p.is_file()}
        expected = {item['path'] for item in inventory}
        if actual_paths != expected:
            raise RuntimeError('Source file set changed during migration; retain source and rerun')
        for item in inventory:
            st = (src / item['path']).stat()
            if (st.st_size, st.st_mtime_ns) != (item['bytes'], item['mtime_ns']):
                raise RuntimeError(f'Source changed before final gate: {item["path"]}')
        state.update(phase='copy_verified_source_retained', current_file=None, current_bytes=0)
        report(True)
        (journal / 'copy_verified.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    except BaseException as exc:
        state.update(phase='stopped_source_retained', error=f'{type(exc).__name__}: {exc}')
        report(True)
        raise


if __name__ == '__main__':
    main()
