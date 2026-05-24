"""Download UCI Hydraulic Systems dataset."""

import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/447/condition+monitoring+of+hydraulic+systems.zip"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "uci"

EXPECTED_FILES = [
    "PS1.txt", "PS2.txt", "PS3.txt", "PS4.txt", "PS5.txt", "PS6.txt",
    "EPS1.txt", "FS1.txt", "FS2.txt",
    "TS1.txt", "TS2.txt", "TS3.txt", "TS4.txt",
    "VS1.txt", "CE.txt", "CP.txt", "SE.txt",
    "profile.txt",
]


def download(url: str, dest: Path) -> Path:
    print(f"Downloading from {url} ...")
    tmp = dest / "_download.zip"
    urllib.request.urlretrieve(url, tmp)
    size_mb = tmp.stat().st_size / 1024 / 1024
    print(f"  Downloaded {size_mb:.1f} MB")
    return tmp


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_recursive(zip_path: Path, dest: Path):
    """Extract zip, then extract any nested zips found inside."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)
    zip_path.unlink()

    for nested in dest.rglob("*.zip"):
        nested_dest = nested.parent
        print(f"  Extracting nested: {nested.name}")
        with zipfile.ZipFile(nested, "r") as zf:
            zf.extractall(nested_dest)
        nested.unlink()


def find_data_files(dest: Path) -> Path:
    """Find directory containing the actual .txt data files (may be nested)."""
    for p in dest.rglob("PS1.txt"):
        return p.parent
    return dest


def verify(data_dir: Path) -> bool:
    missing = [f for f in EXPECTED_FILES if not (data_dir / f).exists()]
    if missing:
        print(f"ERROR: Missing files: {missing}")
        return False
    print(f"  All {len(EXPECTED_FILES)} expected files present.")
    first = data_dir / "PS1.txt"
    with open(first) as f:
        lines = sum(1 for _ in f)
    print(f"  PS1.txt: {lines} cycles (expected ~2205)")
    return True


def main():
    if DATA_DIR.exists() and verify(DATA_DIR):
        print("Data already downloaded and verified. Nothing to do.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    zip_path = download(URL, DATA_DIR)
    digest = sha256(zip_path)
    print(f"  SHA-256: {digest}")

    print("Extracting ...")
    extract_recursive(zip_path, DATA_DIR)

    actual_dir = find_data_files(DATA_DIR)
    if actual_dir != DATA_DIR:
        print(f"  Moving files from {actual_dir} to {DATA_DIR}")
        for f in actual_dir.iterdir():
            shutil.move(str(f), str(DATA_DIR / f.name))
        # clean up empty dirs
        for d in sorted(DATA_DIR.rglob("*"), reverse=True):
            if d.is_dir() and not list(d.iterdir()):
                d.rmdir()

    if verify(DATA_DIR):
        print("\nDone! Data is ready at:", DATA_DIR)
    else:
        print("\nWARNING: Verification failed. Check the data directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()
