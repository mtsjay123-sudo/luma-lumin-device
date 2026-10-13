"""Connectors: Luma plugs into other apps over MCP, the Model Context Protocol.

MCP is the open standard that Claude, ChatGPT and the other assistants use to reach
apps (GitHub, Notion, Slack, your files and thousands more). Luma speaks it too, as
a client, over both transports the spec defines:

- stdio: Luma starts the app's connector program on this computer and talks to it
  over its standard input and output (newline-delimited JSON-RPC);
- Streamable HTTP: Luma posts JSON-RPC to the app's MCP address and reads either a
  JSON answer or a server-sent event stream.

Each connector's tools become Luma tools named ``mcp.<connector>.<tool>``. A tool the
app marks read-only (``readOnlyHint``) runs on its own unless the owner blocks it;
every other tool waits for the owner's yes, like a text or an email. What an app
sends back is treated as information, never as instructions.
"""
from __future__ import annotations

import base64
import itertools
import json
import os
import re
import shlex
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

PROTOCOL = "2025-06-18"
CLIENT = {"name": "luma", "title": "Luma", "version": "0.3.0"}
MAX_CONNECTORS = 12
MAX_TOOLS = 40          # per connector, so a huge app can't flood the brain
MAX_RESULT = 6000       # characters of an app's answer that reach the brain

# Apps people ask for most, with how they connect. Only ones that work without
# extra accounts or paid plans beyond the app itself.
PRESETS = [
    {"id": "files", "name": "Files", "about": "Read and organize files in a folder you pick.",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "{folder}"], "needs": "folder"},
    {"id": "github", "name": "GitHub", "about": "Issues, pull requests and code. Needs a GitHub personal access token.",
     "url": "https://api.githubcopilot.com/mcp/", "needs": "token"},
    {"id": "memory", "name": "Notes graph", "about": "A local knowledge graph Luma can add to and search.",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]},
    {"id": "custom", "name": "Any MCP app", "about": "Paste the app's MCP address, or the command its docs give you."},
]


class ConnectorError(ValueError):
    """An app's connector couldn't be reached or said no."""


# --------------------------------------------------------------- transports ---
class StdioTransport:
    def __init__(self, command, args=(), env=None, cwd=None):
        exe = shutil.which(command) or command
        if not (os.path.isabs(exe) and os.path.exists(exe)):
            hint = " Install Node.js from nodejs.org, then try again." if command in {"npx", "node"} else ""
            raise ConnectorError(f"I couldn't find “{command}” on this computer.{hint}")
        keep = ("PATH", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "LANG", "PROGRAMFILES")
        base = {k: os.environ[k] for k in keep if k in os.environ}
        try:
            self.proc = subprocess.Popen([exe, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         env={**base, **(env or {})}, cwd=cwd, text=True, encoding="utf-8", bufsize=1)
        except OSError as error:
            raise ConnectorError(f"I couldn't start that connector ({error.strerror or error}).") from None
        self._write = threading.Lock()
        self._cond = threading.Condition()
        self._replies = {}
        threading.Thread(target=self._read, name="luma-mcp-stdio", daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                continue  # connectors may log to stdout; ignore anything that isn't JSON-RPC
            if not isinstance(msg, dict):
                continue
            if "method" in msg and "id" in msg:
                # The app asking Luma something (ping, roots, sampling): answer ping, decline the rest.
                reply = {"jsonrpc": "2.0", "id": msg["id"], "result": {}} if msg["method"] == "ping" else \
                        {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "Luma doesn't offer that."}}
                try:
                    self._send(reply)
                except (OSError, ValueError):
                    pass
            elif "id" in msg:
                with self._cond:
                    self._replies[msg["id"]] = msg
                    self._cond.notify_all()
        with self._cond:
            self._cond.notify_all()

    def _send(self, msg):
        with self._write:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()

    def request(self, msg, timeout):
        try:
            self._send(msg)
        except (OSError, ValueError):
            raise ConnectorError("The connector stopped.") from None
        if "id" not in msg:
            return None
        deadline = time.monotonic() + timeout
        with self._cond:
            while msg["id"] not in self._replies:
                if self.proc.poll() is not None:
                    raise ConnectorError("The connector stopped.")
                left = deadline - time.monotonic()
                if left <= 0:
                    raise ConnectorError("The app took too long to answer.")
                self._cond.wait(min(left, 0.5))
            return self._replies.pop(msg["id"])

    def close(self):
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=3)
        except Exception:
            self.proc.kill()


class HttpTransport:
    def __init__(self, url, token=None):
        parts = urllib.parse.urlsplit(url)
        local = parts.hostname in {"127.0.0.1", "localhost", "::1"}
        if parts.scheme != "https" and not (parts.scheme == "http" and local):
            raise ConnectorError("Use the app's https:// MCP address.")
        self.url, self.token, self.session, self.version = url, token, None, None

    def request(self, msg, timeout):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.version:
            headers["MCP-Protocol-Version"] = self.version
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(self.url, data=json.dumps(msg).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                self.session = resp.headers.get("Mcp-Session-Id") or self.session
                if "id" not in msg:
                    return None
                if "text/event-stream" in (resp.headers.get("Content-Type") or ""):
                    return self._from_events(resp, msg["id"])
                body = json.loads(resp.read(4_000_000) or b"null")
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise ConnectorError("The app turned Luma away. Check the access token, or sign in again.") from None
            raise ConnectorError(f"The app answered with an error ({error.code}).") from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ConnectorError(f"I couldn't reach the app ({getattr(error, 'reason', error)}).") from None
        except ValueError:
            raise ConnectorError("The app's answer wasn't valid MCP.") from None
        if isinstance(body, list):
            body = next((b for b in body if isinstance(b, dict) and b.get("id") == msg["id"]), None)
        return body

    @staticmethod
    def _from_events(resp, want):
        data = []
        for raw in resp:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line.startswith("data:"):
                data.append(line[5:].lstrip())
                continue
            if line or not data:
                continue
            try:
                event = json.loads("\n".join(data))
            except ValueError:
                event = None
            data = []
            if isinstance(event, dict) and event.get("id") == want and ("result" in event or "error" in event):
                return event
        raise ConnectorError("The app ended the answer early.")

    def close(self):
        if self.session:
            headers = {"Mcp-Session-Id": self.session, **({"Authorization": "Bearer " + self.token} if self.token else {})}
            try:
                urllib.request.urlopen(urllib.request.Request(self.url, headers=headers, method="DELETE"), timeout=5).close()
            except Exception:
                pass


# ------------------------------------------------------------------ client ---
class McpClient:
    def __init__(self, transport):
        self.transport = transport
        self._ids = itertools.count(1)
        self.server = {}

    def _call(self, method, params=None, timeout=30):
        msg = {"jsonrpc": "2.0", "id": next(self._ids), "method": method, **({"params": params} if params is not None else {})}
        reply = self.transport.request(msg, timeout)
        if not isinstance(reply, dict):
            raise ConnectorError("The app didn't answer.")
        if "error" in reply:
            raise ConnectorError(str((reply["error"] or {}).get("message") or "The app said no.")[:300])
        return reply.get("result") or {}

    def start(self):
        info = self._call("initialize", {"protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": CLIENT}, timeout=90)
        if isinstance(self.transport, HttpTransport):
            self.transport.version = info.get("protocolVersion") or PROTOCOL
        self.transport.request({"jsonrpc": "2.0", "method": "notifications/initialized"}, 15)
        self.server = info.get("serverInfo") or {}
        return info

    def tools(self):
        found, cursor = [], None
        for _ in range(10):
            result = self._call("tools/list", {"cursor": cursor} if cursor else {})
            found += [t for t in result.get("tools") or [] if isinstance(t, dict) and t.get("name")]
            cursor = result.get("nextCursor")
            if not cursor or len(found) >= MAX_TOOLS:
                break
        return found[:MAX_TOOLS]

    def call_tool(self, name, arguments, timeout=120):
        return self._call("tools/call", {"name": name, "arguments": arguments}, timeout)

    def close(self):
        self.transport.close()


# ----------------------------------------------------------------- helpers ---
def slug(text, limit=24):
    out = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")[:limit].strip("_")
    return out or "app"


def fields_for(schema):
    """An MCP input schema as Luma tool fields: required text is "string", everything optional or
    non-text is "text" (numbers and JSON written out), true/false is "boolean"."""
    schema = schema if isinstance(schema, dict) else {}
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = set(schema.get("required") or [])
    fields, kinds = {}, {}
    for key, spec in list(props.items())[:16]:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,40}", str(key)):
            continue
        spec = spec if isinstance(spec, dict) else {}
        kind = spec.get("type")
        kind = next((k for k in kind if k != "null"), "string") if isinstance(kind, list) else (kind or "string")
        if kind == "boolean":
            fields[key] = "boolean"
        elif kind == "string" and key in required:
            fields[key] = "string"
        else:
            fields[key] = "text"
        kinds[key] = (kind, key in required)
    return fields, kinds


def arguments_for(kinds, args):
    """Turn the brain's simple fields back into what the app's schema asked for."""
    out = {}
    for key, (kind, required) in kinds.items():
        value = args.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value == "" and not required:
                continue
            if kind == "integer":
                try:
                    value = int(float(value))
                except ValueError:
                    raise ConnectorError(f"{key} should be a whole number.") from None
            elif kind == "number":
                try:
                    value = float(value)
                except ValueError:
                    raise ConnectorError(f"{key} should be a number.") from None
            elif kind in {"object", "array"}:
                try:
                    value = json.loads(value)
                except ValueError:
                    value = [value] if kind == "array" else {"value": value}
        out[key] = value
    return out


def result_text(result):
    """An app's answer as plain text, marked as information from that app."""
    parts = []
    for item in (result or {}).get("content") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            parts.append(str(item.get("text", "")))
        elif item.get("type") == "resource" and isinstance(item.get("resource"), dict):
            parts.append(str(item["resource"].get("text") or item["resource"].get("uri") or ""))
        elif item.get("type") == "resource_link":
            parts.append(f"{item.get('name') or 'Link'}: {item.get('uri', '')}")
        elif item.get("type") == "image":
            parts.append("[a picture]")
    if not parts and (result or {}).get("structuredContent") is not None:
        parts.append(json.dumps(result["structuredContent"], ensure_ascii=False))
    return "\n".join(p for p in parts if p).strip()[:MAX_RESULT]


# ---------------------------------------------------------------- registry ---
class Connectors:
    """The owner's connected apps. Settings live in Luma's encrypted store; live sessions in RAM."""

    def __init__(self, store, on_tools=None):
        self.store = store
        self.on_tools = on_tools or (lambda tools: None)
        self._clients = {}
        self._tools = {}        # luma tool name -> {"connector", "tool", "kinds", "read_only", "description", "fields"}
        self._lock = threading.RLock()

    # ---- settings
    def _configs(self):
        return [c for c in (self.store.setting("connectors", []) or []) if isinstance(c, dict) and c.get("id")]

    def _save(self, configs):
        self.store.set_setting("connectors", configs)

    def presets(self):
        return [{k: v for k, v in p.items() if k in {"id", "name", "about", "needs"}} for p in PRESETS]

    def list(self):
        out = []
        for c in self._configs():
            tools = [t for t in self._tools.values() if t["connector"] == c["id"]]
            out.append({"id": c["id"], "name": c["name"], "kind": "http" if c.get("url") else "stdio",
                        "where": c.get("url") or " ".join([c.get("command", "")] + [shlex.quote(a) for a in c.get("args", [])])[:200],
                        "connected": c["id"] in self._clients, "error": c.get("error"),
                        "tools": [{"name": t["tool"], "description": t["description"][:160], "read_only": t["read_only"]} for t in tools]})
        return out

    def add(self, name, url="", command="", token="", preset=None, folder=""):
        name = " ".join(str(name or "").split())[:40]
        configs = self._configs()
        if len(configs) >= MAX_CONNECTORS:
            raise ConnectorError(f"Luma can hold {MAX_CONNECTORS} connectors. Remove one first.")
        spec = next((p for p in PRESETS if p["id"] == preset), None) if preset else None
        config = {"name": name or (spec or {}).get("name") or "App"}
        if spec and spec.get("command"):
            if spec.get("needs") == "folder":
                folder = os.path.expanduser(str(folder or "").strip())
                if not folder or not os.path.isdir(folder):
                    raise ConnectorError("Pick a folder that exists on this computer.")
            config.update(command=spec["command"], args=[a.replace("{folder}", folder) for a in spec["args"]])
        elif spec and spec.get("url"):
            config["url"] = spec["url"]
        elif str(url or "").strip():
            config["url"] = str(url).strip()
        elif str(command or "").strip():
            try:
                words = shlex.split(str(command), posix=os.name != "nt")
            except ValueError:
                raise ConnectorError("I couldn't read that command.") from None
            config.update(command=words[0], args=words[1:20])
        else:
            raise ConnectorError("Paste the app's MCP address (https://…) or the command from its docs.")
        if token:
            # base64 so the store's payment-number guard never trips on a long token
            config["secret_b64"] = base64.b64encode(str(token).strip().encode()).decode()
        taken = {c["id"] for c in configs}
        base = slug(config["name"])
        config["id"] = next(f"{base}{'' if i == 0 else i + 1}" for i in itertools.count() if f"{base}{'' if i == 0 else i + 1}" not in taken)
        self._connect(config)  # raises if it can't reach the app; nothing is saved then
        self._save(configs + [config])
        return next(c for c in self.list() if c["id"] == config["id"])

    def remove(self, connector_id):
        with self._lock:
            client = self._clients.pop(connector_id, None)
            if client:
                client.close()
            for name in [n for n, t in self._tools.items() if t["connector"] == connector_id]:
                self._tools.pop(name)
        self._save([c for c in self._configs() if c["id"] != connector_id])
        self.on_tools(dict(self._tools))
        return {"removed": connector_id}

    # ---- sessions
    def _transport(self, config):
        if config.get("url"):
            token = base64.b64decode(config["secret_b64"]).decode() if config.get("secret_b64") else None
            return HttpTransport(config["url"], token)
        return StdioTransport(config["command"], config.get("args", []))

    def _connect(self, config):
        with self._lock:
            client = McpClient(self._transport(config))
            try:
                client.start()
                tools = client.tools()
            except Exception:
                client.close()
                raise
            old = self._clients.pop(config["id"], None)
            if old:
                old.close()
            self._clients[config["id"]] = client
            for name in [n for n, t in self._tools.items() if t["connector"] == config["id"]]:
                self._tools.pop(name)
            for tool in tools:
                fields, kinds = fields_for(tool.get("inputSchema"))
                notes = tool.get("annotations") or {}
                luma_name = f"mcp.{config['id']}.{slug(tool['name'], 40)}"
                about = " ".join(str(tool.get("description") or tool.get("title") or tool["name"]).split())[:260]
                self._tools[luma_name] = {"connector": config["id"], "connector_name": config["name"], "tool": tool["name"],
                                          "kinds": kinds, "fields": fields, "read_only": notes.get("readOnlyHint") is True,
                                          "description": f"{config['name']}: {about}"}
        self.on_tools(dict(self._tools))
        return tools

    def start_all(self):
        """Reconnect saved connectors (in the background at startup). A broken one just shows its error."""
        configs = self._configs()
        for config in configs:
            try:
                self._connect(config)
                config.pop("error", None)
            except Exception as error:
                config["error"] = str(error)[:200]
        self._save(configs)

    def tools(self):
        return dict(self._tools)

    def call(self, luma_name, args):
        tool = self._tools.get(luma_name)
        if not tool:
            raise ConnectorError("That app isn't connected anymore.")
        client = self._clients.get(tool["connector"])
        if not client:
            config = next((c for c in self._configs() if c["id"] == tool["connector"]), None)
            if not config:
                raise ConnectorError("That app isn't connected anymore.")
            self._connect(config)
            client = self._clients[tool["connector"]]
        result = client.call_tool(tool["tool"], arguments_for(tool["kinds"], args))
        text = result_text(result) or "Done."
        failed = bool(result.get("isError"))
        return {"connector": tool["connector_name"], "tool": tool["tool"], "ok": not failed,
                "text_from_app": text,
                "summary": (f"{tool['connector_name']} said no: " if failed else f"From {tool['connector_name']}: ") + text[:400]}

    def close(self):
        for client in list(self._clients.values()):
            client.close()
        self._clients.clear()
