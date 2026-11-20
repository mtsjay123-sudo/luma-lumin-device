#!/usr/bin/env python3
"""Rule 7, checked: every package Luma depends on is MIT, Apache-2.0 or BSD.

Reads the licenses the installed packages declare about themselves (their own metadata), for Luma's direct dependencies
(pyproject.toml) and everything those pull in. Each one lands in one of four piles:

- allowed:      MIT, Apache-2.0, BSD
- permissive:   not on the list, but the same kind (ISC, PSF, Zlib, HPND, Unlicense, 0BSD): named, for a person to decide
- not allowed:  GPL, LGPL, AGPL, MPL, EPL, CC BY-NC, SSPL and anything "non-commercial"
- unknown:      the package doesn't say, or isn't installed here

It fails (exit 1) when a direct dependency is not allowed. Everything else is printed so a person can look.
This reads what packages say about themselves. It isn't legal advice, and models and voices have licenses of their
own that this doesn't see (those are checked by hand, in docs/).

  python scripts/license_check.py            # the table
  python scripts/license_check.py --strict   # also fail on unknown or not-allowed packages pulled in by others
  pip install --dry-run --ignore-installed --report out/pip.json ".[agent]" && python scripts/license_check.py --report out/pip.json
                                             # everything Luma would install, without installing any of it
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALLOWED = re.compile(r"\b(?:MIT|Apache(?:[- ]2(?:\.0)?| Software License| License)?|BSD|Expat)\b", re.I)
PERMISSIVE = re.compile(r"\b(?:ISC|PSF|Python Software Foundation|Zlib|HPND|MIT-CMU|Unlicense|0BSD|Public Domain|CC0)\b", re.I)
NOT_ALLOWED = re.compile(r"\b(?:A?GPL|LGPL|Lesser General Public|General Public License|Affero|MPL|Mozilla Public|EPL|Eclipse Public|SSPL|"
                         r"CC[- ]BY[- ]NC|Non[- ]?Commercial|Commons Clause|Business Source|BUSL)\b", re.I)


def _name(requirement):
    return re.split(r"[\s\[<>=!~;(]", requirement.strip(), maxsplit=1)[0].lower().replace("_", "-")


def direct():
    """Luma's own dependencies, from pyproject.toml (the optional ones too)."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    names = [_name(r) for r in project.get("dependencies", [])]
    for extra in (project.get("optional-dependencies") or {}).values():
        names += [_name(r) for r in extra]
    return sorted(set(names))


def declared(dist):
    """What a package says its license is: the license field, then its classifiers."""
    meta = dist.metadata
    said = [meta.get("License-Expression") or "", meta.get("License") or ""]
    said += [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    said = [s.strip() for s in said if s and s.strip() and s.strip().upper() != "UNKNOWN"]
    return "; ".join(dict.fromkeys(s if len(s) < 80 else s[:77] + "..." for s in said))


def pile(text):
    if not text:
        return "unknown"
    if NOT_ALLOWED.search(text) and not (ALLOWED.search(text) and re.search(r"\bOR\b|;", text)):  # "MIT OR GPL": the allowed one may be chosen
        return "not allowed"
    if ALLOWED.search(text):
        return "allowed"
    if PERMISSIVE.search(text):
        return "permissive"
    return "unknown"


def closure(names):
    """Every installed package these pull in: {name: (license text, pile, direct?)}."""
    seen, todo, out = set(), list(names), {}
    first = set(names)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            out[name] = ("(not installed here)", "unknown", name in first)
            continue
        text = declared(dist)
        out[name] = (text, pile(text), name in first)
        for req in dist.requires or []:
            if "extra ==" in req:
                continue  # an optional extra of theirs: only what's installed by default counts
            todo.append(_name(req))
    return out


def from_report(path, names):
    """The same, from pip's own report of what it would install (`pip install --dry-run --report FILE .`), so nothing
    has to be installed: {name: (license text, pile, direct?)}."""
    import json
    first, out = set(names), {}
    for item in json.loads(Path(path).read_text()).get("install", []):
        meta = item.get("metadata") or {}
        name = str(meta.get("name") or "").lower().replace("_", "-")
        if not name or name == "luma":
            continue
        said = [meta.get("license_expression") or "", meta.get("license") or ""]
        said += [c.split("::")[-1].strip() for c in meta.get("classifier") or [] if c.startswith("License ::")]
        said = [x.strip() for x in said if x and x.strip() and x.strip().upper() != "UNKNOWN"]
        text = "; ".join(dict.fromkeys(x if len(x) < 80 else x[:77] + "..." for x in said))
        out[name] = (text, pile(text), name in first)
    for name in first - set(out):
        out[name] = ("(pip didn't pick it for this machine)", "unknown", True)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--report", help="pip's report of what it would install, instead of what's installed here")
    args = parser.parse_args()
    found = from_report(args.report, direct()) if args.report else closure(direct())
    order = {"not allowed": 0, "unknown": 1, "permissive": 2, "allowed": 3}
    rows = sorted(found.items(), key=lambda kv: (order[kv[1][1]], not kv[1][2], kv[0]))
    counts = {k: sum(1 for _, (_, p, _) in rows if p == k) for k in order}
    print(f"{len(rows)} packages: {counts['allowed']} allowed, {counts['permissive']} permissive but not on the list, "
          f"{counts['not allowed']} not allowed, {counts['unknown']} unknown\n")
    for name, (text, kind, is_direct) in rows:
        if kind != "allowed":
            print(f"  {kind:<12} {'direct  ' if is_direct else 'pulled in'} {name:<28} {text}")
    bad_direct = [n for n, (_, p, d) in rows if d and p == "not allowed"]
    bad_any = [n for n, (_, p, _) in rows if p in ("not allowed", "unknown")]
    if bad_direct:
        print("\nNot allowed, and Luma depends on it directly: " + ", ".join(bad_direct))
        return 1
    if args.strict and bad_any:
        print("\n--strict: not allowed or unknown: " + ", ".join(bad_any))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
