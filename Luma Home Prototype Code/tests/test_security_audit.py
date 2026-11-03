"""Luma's security review of the code it writes: the common mistakes are found with where they are and how to fix them,
the safe way of writing the same thing is left alone, and in the code studio a high finding goes back to the coding
agent the way a failing test does, so the code that reaches the owner has it fixed."""
import tempfile
import unittest
from pathlib import Path

import work_fakes
from luma.memory.store import Store
from luma.work import security_audit as audit
from luma.work.engine import Engine
from luma.work.projects import Projects

KEY = "sk-ant-" + "a1B2c3D4e5F6g7H8i9J0kLmN"  # assembled here so this file itself doesn't carry a key-shaped string

FLAWS = {
    "secret": ("app.py", f'client = Anthropic(api_key="{KEY}")'),
    "password": ("db.py", 'DB_PASSWORD = "hunter2-prod"'),
    "sql": ("users.py", 'cur.execute(f"SELECT * FROM users WHERE name = \'{name}\'")'),
    "shell": ("tools.py", 'subprocess.run(f"convert {path} out.png", shell=True)'),
    "eval": ("calc.py", "result = eval(input('> '))"),
    "deserialize": ("load.py", "state = pickle.loads(request.data)"),
    "tls": ("fetch.py", "requests.get(url, verify=False)"),
    "xss": ("app.js", "list.innerHTML = `<li>${message}</li>`;"),
    "hash": ("auth.py", "stored = hashlib.md5(password.encode()).hexdigest()"),
    "debug": ("server.py", "app.run(debug=True)"),
}
SAFE = {
    "app.py": 'client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])',
    "users.py": 'cur.execute("SELECT * FROM users WHERE name = ?", (name,))',
    "tools.py": 'subprocess.run(["convert", path, "out.png"])',
    "calc.py": "result = ast.literal_eval(text)",
    "load.py": "state = json.loads(request.data)",
    "app.js": "item.textContent = message;",
    "auth.py": "stored = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)",
    "config.py": 'PASSWORD = os.environ.get("APP_PASSWORD", "changeme")',
    "test_login.py": 'self.login(password="hunter2-prod")',
}


class AuditTests(unittest.TestCase):
    def test_each_common_mistake_is_found_and_explained(self):
        for rule, (path, line) in FLAWS.items():
            found = audit.audit_text(line, path)
            self.assertEqual([f["rule"] for f in found], [rule], f"{path}: {line}")
            self.assertTrue(found[0]["fix"] and found[0]["what"])
            self.assertEqual(found[0]["line"], 1)

    def test_the_safe_way_is_left_alone(self):
        for path, line in SAFE.items():
            self.assertEqual(audit.audit_text(line, path), [], f"{path}: {line}")

    def test_comments_and_allowed_lines_are_skipped(self):
        self.assertEqual(audit.audit_text("# never do: requests.get(url, verify=False)", "a.py"), [])
        self.assertEqual(audit.audit_text("requests.get(url, verify=False)  # luma: allow (local test server)", "a.py"), [])

    def test_a_folder_report_worst_first(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "app.py").write_text("import os\napp.run(debug=True)\nrequests.get(url, verify=False)\n")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "lib.js").write_text("eval(code)")
            findings = audit.audit_folder(root)
        self.assertEqual([(f["severity"], f["line"]) for f in findings], [("high", 3), ("medium", 2)], "dependencies aren't ours to review")
        text = audit.report(findings)
        self.assertIn("1 high, 1 medium.", text)
        self.assertIn("## High: app.py:3", text)
        self.assertIn("No common security mistakes found", audit.report([]))


class CodeStudioSecurityTests(unittest.TestCase):
    def test_a_hole_goes_back_to_the_coder_and_comes_back_fixed(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        store = Store(root / "s.db", root / "k")
        self.addCleanup(store.close)
        projects = Projects(store, root / "projects")
        tries = []

        def code(n):
            tries.append(n)
            query = ('cur.execute(f"SELECT * FROM notes WHERE tag = \'{tag}\'")' if n == 1 else 'cur.execute("SELECT * FROM notes WHERE tag = ?", (tag,))')
            return {"folder": "notes", "files": [{"path": "notes.py", "content": f"def find(cur, tag):\n    {query}\n    return cur.fetchall()\n"}],
                    "test_command": "", "run_command": ""}
        brain = work_fakes.Brain({"work.code": code})
        engine = Engine(projects, think=brain, search=work_fakes.search, approver=lambda q: True, render=False)
        project = projects.create("Notes", "")
        engine.allow_code(project["id"])
        run = engine.start(project["id"], "write a python script that finds my notes by tag")
        step = next(s for s in run["steps"] if s["tool"] == "code")
        self.assertEqual(tries, [1, 2], "the first try had SQL injection, so it went back with the reason")
        retry = [c["prompt"] for c in brain.calls if c["name"] == "work.code"][1]
        self.assertIn("SQL injection", retry, "the coder is told what's wrong and how to fix it")
        self.assertIn("notes.py:2", retry)
        self.assertEqual(step["state"], "done")
        report = (projects.folder(project["id"]) / "code/notes/SECURITY.md").read_text()
        self.assertIn("No common security mistakes found", report)
        self.assertIn("security review clean", step["summary"])


if __name__ == "__main__":
    unittest.main()
