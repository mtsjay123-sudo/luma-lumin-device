"""Tasks the owner taught Luma by doing them once in Luma's browser.

While the owner drives Luma's browser with Teach on, each click, typed field and
Enter is kept as a step, described by what it says on the page (the button's
words, the field's label), not by where it sat on the screen. Passwords are
never kept. Replaying a task goes through the same approval rules as anything
else Luma does: buying, sending, posting or submitting still waits for the owner.
"""
from __future__ import annotations

import re
import time

MAX_STEPS = 40


def _norm(text):
    return " ".join(re.findall(r"[a-z0-9$]+", str(text or "").lower()))


class Recorder:
    """One teaching session, held by the control server while Teach is on."""

    def __init__(self, start_url):
        self.start_url = start_url
        self.steps = []

    def add(self, kind, data, result):
        target = (result or {}).get("target")
        last = self.steps[-1] if self.steps else None
        if kind == "go":
            self.steps.append({"do": "open", "url": (result or {}).get("url") or data.get("url")})
        elif kind == "click" and target:
            self.steps.append({"do": "click", "target": target})
        elif kind == "type" and target:
            secret = target.get("type") == "password"
            if last and last["do"] == "type" and last["target"] == target:
                if not secret: last["text"] = (last.get("text", "") + str(data.get("text", "")))[:500]
            else:
                self.steps.append({"do": "type", "target": target, "text": "" if secret else str(data.get("text", ""))[:500], "secret": secret})
        elif kind == "key" and data.get("key") == "Enter":
            if last and last["do"] == "type": last["submit"] = True
            else: self.steps.append({"do": "key", "key": "Enter"})
        elif kind == "back":
            self.steps.append({"do": "key", "back": True})
        del self.steps[MAX_STEPS:]
        return len(self.steps)


def best_match(elements, target):
    """The element on the page now that is the one the owner used, or None."""
    want_label, want_name, want_hint = _norm(target.get("label")), _norm(target.get("name")), _norm(target.get("placeholder"))
    best, best_score = None, 0
    for el in elements:
        label = _norm(el.get("label"))
        score = 0
        if want_label and label == want_label: score += 10
        elif want_label and len(want_label) > 3 and (want_label in label or (label and label in want_label and len(label) > 3)): score += 6
        if want_name and _norm(el.get("name")) == want_name: score += 6
        if want_hint and _norm(el.get("placeholder")) == want_hint: score += 6
        if el.get("tag") == target.get("tag"): score += 1
        if target.get("href") and el.get("href") and el["href"].split("?")[0] == target["href"].split("?")[0]: score += 5
        if score > best_score:
            best, best_score = el, score
    return best["ref"] if best and best_score >= 6 else None


class Taught:
    def __init__(self, agent):
        self.agent = agent
        self.store = agent.store

    def list(self):
        rows = self.store.all("taught", 60)
        return [{"id": r["id"], "name": r["name"], "steps": len(r["steps"]), "site": r.get("site", ""), "created": r.get("created"), "runs": r.get("runs", 0)}
                for r in sorted(rows, key=lambda r: r.get("created", 0), reverse=True)]

    def save(self, name, recorder):
        name = " ".join(str(name or "").split())[:60]
        if len(name) < 2: raise ValueError("Give it a short name, like “order my usual coffee”.")
        if not recorder or not recorder.steps: raise ValueError("Show me at least one step first: click or type on the page while Teach is on.")
        if any(_norm(r["name"]) == _norm(name) for r in self.store.all("taught", 60)):
            raise ValueError("You already taught me something with that name. Pick another.")
        from urllib.parse import urlsplit
        steps = [{**s, "text": "" if s.get("secret") else s.get("text", "")} for s in recorder.steps]
        return self.store.put("taught", {"name": name, "start_url": recorder.start_url, "steps": steps, "site": (urlsplit(recorder.start_url).hostname or "").removeprefix("www."),
                                         "created": self.agent.clock(), "runs": 0})

    def delete(self, ident):
        return self.store.delete("taught", str(ident))

    def find(self, words, exact=False):
        want = _norm(words)
        rows = self.store.all("taught", 60)
        same = next((r for r in rows if _norm(r["name"]) == want), None)
        if same or exact:
            return same
        return next((r for r in rows if len(want) > 3 and (want in _norm(r["name"]) or _norm(r["name"]) in want)), None)

    def run(self, row, cancel_event=None):
        """Do it again, step by step, through Luma's normal approval rules."""
        agent, name = self.agent, row["name"]
        agent.activity.start("taught", f"Doing “{name}”")
        try:
            agent.propose("browser.open", {"url": row["start_url"]})
            for number, step in enumerate(row["steps"], 1):
                if cancel_event is not None and cancel_event.is_set():
                    return {"text": f"Stopped “{name}” at step {number}.", "state": "stopped"}
                agent.activity.step(self._say(step))
                if step["do"] == "open":
                    agent.propose("browser.open", {"url": step["url"]})
                    continue
                if step["do"] == "key":
                    agent.browser.drive("back" if step.get("back") else "key", {} if step.get("back") else {"key": "Enter"})
                    continue
                if step.get("secret"):
                    page = agent.browser.read()
                    if not any(e.get("type") == "password" for e in page.get("elements", [])):
                        continue  # already signed in: nothing to type
                    agent.pending_handoff = {"kind": "sign_in", "site": row.get("site") or "this site", "url": page.get("url"), "retry": f"run {name}"}
                    return {"text": f"“{name}” needs you to sign in to {row.get('site') or 'the site'} first. Sign in once in Luma's browser (I never type passwords), then say \"done\".",
                            "sign_in": row.get("site") or "the site", "url": page.get("url"), "section": "apps"}
                page = agent.browser.read()
                ref = best_match(page.get("elements", []), step["target"])
                if ref is None:
                    label = step["target"].get("label") or step["target"].get("placeholder") or "the next thing"
                    return {"text": f"I got to step {number} of “{name}”, but I can't find “{label}” on the page anymore. The site may have changed. Want to show me again?",
                            "url": page.get("url"), "handoff": True}
                if step["do"] == "click":
                    result = agent.propose("browser.click", {"ref": ref})
                else:
                    result = agent.propose("browser.type", {"ref": ref, "text": step.get("text", ""), "submit": bool(step.get("submit"))})
                if result.get("state") == "pending":
                    result["text"] = f"I did “{name}” up to the last part. {self._say(step)} needs your OK, so take a look and press Allow if it's right."
                    return result
                time.sleep(0.2)
            fresh = self.store.get("taught", row["id"]) or row
            fresh["runs"] = fresh.get("runs", 0) + 1
            self.store.put("taught", fresh, row["id"])
            return {"text": f"Done: “{name}”. It's open in Luma's browser if you want to look.", "url": agent.browser.read().get("url"), "taught": row["id"]}
        finally:
            agent.activity.finish(f"“{name}”")

    @staticmethod
    def _say(step):
        target = step.get("target") or {}
        label = target.get("label") or target.get("placeholder") or target.get("name") or "it"
        if step["do"] == "click": return f"Pressing “{label}”"
        if step["do"] == "type": return f"Filling in “{label}”"
        if step["do"] == "open": return "Opening the page"
        return "Pressing Enter" if step.get("key") else "Going back"
