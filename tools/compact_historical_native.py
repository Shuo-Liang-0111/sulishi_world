"""Losslessly NTFS-compress two explicit inactive checkpoints; never move/delete.

This changes file-system storage only, not Blender encoding or file contents.
All resolved paths must stay in this project's native folder. A full SHA256 is
checked before and after each file and a receipt is persisted after each step.
"""
from pathlib import Path
import ctypes
from ctypes import wintypes
import hashlib
import json
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "G1_014r2_service_details_working.blend1",
    "G1_013_south_public_space_working.blend",
]
RECEIPT = ROOT / "evidence/storage/ntfs_pre023.json"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def allocated(path):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = kernel.GetCompressedFileSizeW
    fn.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    fn.restype = wintypes.DWORD
    high = wintypes.DWORD()
    ctypes.set_last_error(0)
    low = fn(str(path), ctypes.byref(high))
    if low == 0xffffffff and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    return (high.value << 32) | low


def main():
    probe = subprocess.run(["powershell", "-NoProfile", "-Command",
        "@(Get-Process blender -ErrorAction SilentlyContinue).Count"],
        capture_output=True, text=True, check=True)
    if int(probe.stdout.strip()):
        raise RuntimeError("Close Blender before storage maintenance.")
    if RECEIPT.exists():
        raise RuntimeError("Existing receipt preserved; inspect before rerunning.")
    native = (ROOT / "native").resolve(strict=True)
    targets = [(native / n).resolve(strict=True) for n in FILES]
    for p in targets:
        if p.parent != native or p.name not in FILES:
            raise RuntimeError(f"Unexpected resolved path: {p}")
        with p.open("rb") as f:
            if f.read(7) != b"BLENDER":
                raise RuntimeError(f"Not an expected raw Blender file: {p.name}")
    result = {"operation": "NTFS transparent compression; no deletion/move",
              "started_unix": time.time(), "free_before": shutil.disk_usage(ROOT).free,
              "files": [], "complete": False}
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    for p in targets:
        row = {"path": p.relative_to(ROOT).as_posix(), "size": p.stat().st_size,
               "sha256_before": sha(p), "allocated_before": allocated(p)}
        result["files"].append(row)
        RECEIPT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("NTFS_START", p.name, flush=True)
        run = subprocess.run(["compact.exe", "/C", str(p)], capture_output=True)
        row.update({"exit_code": run.returncode, "allocated_after": allocated(p),
                    "sha256_after": sha(p), "size_after": p.stat().st_size})
        row["content_identical"] = (row["sha256_before"] == row["sha256_after"]
                                    and row["size"] == row["size_after"])
        result["free_after"] = shutil.disk_usage(ROOT).free
        RECEIPT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        if run.returncode or not row["content_identical"]:
            raise RuntimeError(f"Compression/check failed, preserved file: {p.name}")
        print(json.dumps(row), flush=True)
    result["complete"] = True
    result["finished_unix"] = time.time()
    RECEIPT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("NTFS_COMPLETE", result["free_after"] - result["free_before"], flush=True)


if __name__ == "__main__":
    main()
