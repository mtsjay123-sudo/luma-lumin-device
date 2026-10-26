"""Skill notes: SKILL.md folders, the same format Claude Code and Hermes Agent use.

A skill is a folder holding a SKILL.md: front matter (name, description, and optionally
version, license, platforms and tags) followed by plain instructions. When a request
matches a skill's description, its instructions go into that turn as guidance.

Guidance only. A skill can't add tools, unlock anything the owner's rules block, or change
what needs a yes, and adding a new one waits for the owner's yes like anything else that
changes what Luma does.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
BODY_LIMIT = 4000  # per skill, in a turn
FILE_LIMIT = 64_000
STOP = set("a an and are as at be but by can do for from get had has have how i if in into is it its just me my of on or "
           "our out so that the their them then there these they this to up us use used uses using was we what when where "
           "which who why will with you your".split())


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", str(text).casefold()) if len(w) > 2 and w not in STOP}


def _front(text):
    """The front matter as a dict. PyYAML when it's installed, else the simple key: value lines skills use."""
    try:
        import yaml
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ImportError:
        pass
    except Exception:
        raise ValueError("The SKILL.md front matter isn't valid.")
    data = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and m.group(2):
            data[m.group(1)] = m.group(2).strip().strip("'\"")
    tags = re.search(r"^\s*tags:\s*\[(.*?)\]", text, re.M)
    if tags:
        data["tags"] = [t.strip().strip("'\"") for t in tags.group(1).split(",") if t.strip()]
    return data


def parse(text):
    """A SKILL.md, checked: {name, description, version, tags, body}. Raises ValueError when it isn't one."""
    text = str(text or "").replace("\r\n", "\n")
    if len(text) > FILE_LIMIT:
        raise ValueError("That skill is too long.")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("A SKILL.md starts with front matter between --- lines.")
    meta, body = _front(m.group(1)), m.group(2).strip()
    name = str(meta.get("name") or "").strip().casefold()
    description = " ".join(str(meta.get("description") or "").split())
    if not NAME.fullmatch(name):
        raise ValueError("A skill needs a short name: lowercase letters, numbers and dashes.")
    if not description:
        raise ValueError("A skill needs a description that says when to use it.")
    if not body:
        raise ValueError("That skill has no instructions.")
    metadata = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
    hermes = metadata.get("hermes") if isinstance(metadata.get("hermes"), dict) else {}
    tags = meta.get("tags") or hermes.get("tags") or []
    tags = [str(t) for t in tags][:20] if isinstance(tags, list) else []
    return {"name": name, "description": description[:600], "version": str(meta.get("version") or "")[:20], "tags": tags, "body": body}


def preview(text):
    """What the owner sees on the approval card before a skill is added."""
    skill = parse(text)
    return {"skill": skill["name"], "use_it_for": skill["description"][:300], "starts_with": " ".join(skill["body"].split())[:240]}


class SkillNotes:
    def __init__(self, folder):
        self.folder = Path(folder)
        self._cache = (None, [])

    def all(self):
        """Every valid skill in the folder; broken ones are skipped, not fatal."""
        try:
            files = sorted(self.folder.glob("*/SKILL.md"))
            stamp = tuple((str(f), f.stat().st_mtime) for f in files)
        except OSError:
            return []
        if stamp == self._cache[0]:
            return self._cache[1]
        skills = []
        for f in files:
            try:
                skills.append({**parse(f.read_text(encoding="utf-8", errors="replace")), "folder": f.parent.name})
            except Exception:  # broken or odd skills are skipped, never fatal
                continue
        self._cache = (stamp, skills)
        return skills

    def list(self):
        return [{k: s[k] for k in ("name", "description", "version", "tags")} for s in self.all()]

    def match(self, text, limit=2):
        """The skills whose name, description and tags share enough words with this request, best first."""
        asked = words(text)
        if not asked:
            return []
        scored = []
        said = " ".join(re.findall(r"[a-z0-9]+", str(text).casefold()))
        for s in self.all():
            spoken = s["name"].replace("-", " ")
            name_hit = len(s["name"]) >= 4 and re.search(r"\b" + re.escape(spoken) + r"\b", said) is not None
            shared = asked & (words(s["description"]) | words(" ".join(s["tags"])) | words(s["name"].replace("-", " ")))
            if name_hit or len(shared) >= 2:
                scored.append((len(shared) + (3 if name_hit else 0), s))
        scored.sort(key=lambda p: -p[0])
        return [s for _, s in scored[:limit]]

    def notes(self, text):
        """The prompt lines for this request: each matching skill's instructions, trimmed."""
        return [f"Skill “{s['name']}” ({s['description']}):\n{s['body'][:BODY_LIMIT]}" for s in self.match(text)]

    def install(self, text):
        """Write a checked SKILL.md into its own folder. Call only after the owner said yes."""
        skill = parse(text)
        where = self.folder / skill["name"]
        where.mkdir(parents=True, exist_ok=True)
        (where / "SKILL.md").write_text(str(text).replace("\r\n", "\n"), encoding="utf-8")
        self._cache = (None, [])
        return {k: skill[k] for k in ("name", "description", "version", "tags")}

    def remove(self, name):
        name = str(name or "").strip().casefold()
        if not NAME.fullmatch(name):
            raise ValueError("That isn't a skill name.")
        skill = next((s for s in self.all() if s["name"] == name), None)
        if not skill:
            raise ValueError("There's no skill called that.")
        where = self.folder / skill["folder"]
        target = where / "SKILL.md"
        target.unlink()
        for leftover in where.iterdir():
            # a skill folder can carry helper files; Luma never runs them, so they go too
            if leftover.is_file(): leftover.unlink()
        try: where.rmdir()
        except OSError: pass
        self._cache = (None, [])
        return {"removed": name}


def folder_for(store):
    return Path(os.environ.get("LUMA_SKILLS_DIR") or (Path(store.db_path).parent / "skills"))
