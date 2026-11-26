"""Make a release of Luma's code, and the key that signs it (docs/PRESENCE_MASTER_PROMPT.md, 9.1).

    python scripts/release.py keygen                      a new release key: the private half is printed once, for the owner to keep offline
    python scripts/release.py build --version 0.2.0 --key-file ~/luma-release.key --out out/release [--share 0.01]

build writes three files into --out: the code archive, manifest.json and manifest.sig. Those three are what an update
server serves. The private key never goes in the repository or on a device.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from luma.update import release  # noqa: E402


def archive(source: Path) -> bytes:
    """The luma package as one .tar.gz: plain files only, no caches, the same bytes for the same code."""
    import gzip
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as packed, tarfile.open(fileobj=packed, mode="w") as tar:
        for path in sorted(source.rglob("*")):
            if "__pycache__" in path.parts or path.suffix == ".pyc" or not (path.is_file() or path.is_dir()) or path.is_symlink():
                continue
            info = tar.gettarinfo(str(path), arcname=str(Path("luma") / path.relative_to(source)))
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            if path.is_file():
                with open(path, "rb") as f:
                    tar.addfile(info, f)
            else:
                tar.addfile(info)
    return out.getvalue()


def build(version, private_key, out, share=1.0, source=None, notes=""):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    release.number(version)
    data = archive(Path(source) if source else ROOT / "src" / "luma")
    name = f"luma-{version}.tar.gz"
    manifest = release.check({"version": version, "made": int(time.time()), "share": share, "notes": notes[:400],
                              "pieces": [{"name": "code", "file": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}]})
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_bytes(data)
    (out / "manifest.json").write_bytes(release.canonical(manifest))
    (out / "manifest.sig").write_text(release.sign(manifest, key))
    return manifest


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="what", required=True)
    sub.add_parser("keygen")
    b = sub.add_parser("build")
    b.add_argument("--version", required=True)
    b.add_argument("--key-file", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--share", type=float, default=1.0)
    b.add_argument("--notes", default="")
    args = parser.parse_args()
    if args.what == "keygen":
        private, public = release.keygen()
        print("Private half (keep it offline; it is shown once):", private)
        print("Public half (goes in PUBLIC_KEYS in src/luma/update/release.py):", public)
        return
    manifest = build(args.version, Path(args.key_file).expanduser().read_text().strip(), args.out, args.share, notes=args.notes)
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
