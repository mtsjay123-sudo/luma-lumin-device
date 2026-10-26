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

# One sign-in, 1,500+ apps: Composio's hosted MCP server. People sign in with their own Composio account in the browser (no
# developer key), then connect each app (Gmail, Calendar, Slack…) on that app's own consent page. The same idea Open Dot uses.
COMPOSIO_MCP = "https://connect.composio.dev/mcp"
# Hub tools that run code on someone else's machine or manage the hub itself: Luma doesn't take them.
HUB_HIDDEN = re.compile(r"REMOTE_BASH|REMOTE_WORKBENCH|SKILL|SUBMIT_FEEDBACK|WAIT_FOR_CONNECTIONS")
# An action that only reads (GMAIL_FETCH_EMAILS, GOOGLECALENDAR_LIST_EVENTS) runs on its own. Send, post, create, update, delete ask first.
READ_VERB = re.compile(r"_(?:GET|LIST|SEARCH|FETCH|FIND|READ|RETRIEVE|QUERY|DESCRIBE|LOOKUP|VIEW|CHECK|COUNT)(?:_|$)")
# ...and a name that also says it changes something ("…_SEARCH_AND_DELETE") always asks.
WRITE_VERB = re.compile(r"_(?:SEND|CREATE|UPDATE|DELETE|REMOVE|POST|PUT|PATCH|ADD|MOVE|TRASH|ARCHIVE|REPLY|FORWARD|INVITE|SHARE|UPLOAD|SET|STAR|"
                        r"MARK|MODIFY|EDIT|WRITE|INSERT|APPEND|CLEAR|CANCEL|ACCEPT|DECLINE|SCHEDULE|PUBLISH|LIKE|FOLLOW|BLOCK|BAN|KICK|PIN|EXECUTE|"
                        r"RUN|TRIGGER|ENABLE|DISABLE|MERGE|CLOSE|START|STOP|BATCH|PURCHASE|BUY|ORDER|PAY|TRANSFER|SUBMIT|APPROVE|REJECT)(?:_|$)")


def only_reads(slug_):
    slug_ = str(slug_ or "").upper()
    return bool(READ_VERB.search(slug_)) and not WRITE_VERB.search(slug_)
APP_NAMES = {"gmail": "Gmail", "googlecalendar": "Google Calendar", "googledrive": "Google Drive", "googledocs": "Google Docs",
             "googlesheets": "Google Sheets", "outlook": "Outlook", "slack": "Slack", "notion": "Notion", "github": "GitHub", "linear": "Linear",
             "linkedin": "LinkedIn", "youtube": "YouTube", "reddit": "Reddit", "spotify": "Spotify", "discord": "Discord", "trello": "Trello",
             "dropbox": "Dropbox", "hubspot": "HubSpot", "figma": "Figma", "calendly": "Calendly", "zoom": "Zoom", "airtable": "Airtable"}


# Words that mean an app the hub can reach: its tools are offered to the brain when one comes up.
HUB_WORDS = re.compile(r"\b(?:gmail|e-?mails?|inbox|calendar|meeting|events?|drive|google docs?|sheets?|slack|notion|outlook|github|linear|linkedin|"
                       r"youtube|reddit|spotify|discord|trello|dropbox|hubspot|figma|calendly|zoom|airtable)\b", re.I)


def app_name(slug):
    return APP_NAMES.get(slug) or str(slug).replace("_", " ").title()

# Apps people ask for most, with how they connect. Only ones that work without
# extra accounts or paid plans beyond the app itself.
PRESETS = [
    {"id": "files", "name": "Files", "about": "Read and organize files in a folder you pick.",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "{folder}"], "needs": "folder"},
    {"id": "github", "name": "GitHub", "about": "Issues, pull requests and code. Needs a GitHub personal access token.",
     "url": "https://api.githubcopilot.com/mcp/", "needs": "token"},
    {"id": "huggingface", "name": "Hugging Face", "about": "Models, datasets, Spaces and papers. Needs a Hugging Face access token (huggingface.co/settings/tokens).",
     "url": "https://huggingface.co/mcp", "needs": "token"},
    {"id": "supabase", "name": "Supabase", "about": "Your Supabase projects, tables and logs, read-only. Needs a Supabase personal access token (supabase.com/dashboard/account/tokens).",
     "url": "https://mcp.supabase.com/mcp?read_only=true", "needs": "token"},
    {"id": "figma", "name": "Figma", "about": "Your open designs. In the Figma desktop app, switch to Dev Mode and turn on the desktop MCP server first.",
     "url": "http://127.0.0.1:3845/mcp"},
    {"id": "aws", "name": "AWS", "about": "Your AWS account through the AWS CLI's sign-in on this computer. Needs uv (astral.sh/uv) and AWS credentials set up.",
     "command": "uvx", "args": ["awslabs.aws-api-mcp-server@latest"]},
    {"id": "memory", "name": "Notes graph", "about": "A local knowledge graph Luma can add to and search.",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]},
    # Sign in with the app itself, the way ChatGPT and Claude connect: no codes, no tokens.
    {"id": "notion", "name": "Notion", "about": "Your pages and databases. Press Connect and sign in to Notion.", "url": "https://mcp.notion.com/mcp", "needs": "signin"},
    {"id": "linear", "name": "Linear", "about": "Your issues and projects. Press Connect and sign in to Linear.", "url": "https://mcp.linear.app/mcp", "needs": "signin"},
    {"id": "atlassian", "name": "Jira & Confluence", "about": "Atlassian's Jira and Confluence. Press Connect and sign in.", "url": "https://mcp.atlassian.com/v1/sse", "needs": "signin"},
    {"id": "asana", "name": "Asana", "about": "Your tasks and projects. Press Connect and sign in to Asana.", "url": "https://mcp.asana.com/sse", "needs": "signin"},
    {"id": "stripe", "name": "Stripe", "about": "Payments, customers and invoices. Press Connect and sign in to Stripe.", "url": "https://mcp.stripe.com", "needs": "signin"},
    # One sign-in, then Gmail, Calendar, Slack, Notion and 1,500+ more, each with one Allow on the app's own page.
    {"id": "apps", "name": "Gmail & 1,500+ apps", "about": "Gmail, Google Calendar, Drive, Slack, Notion, Outlook and 1,500+ more, through Composio. "
     "Press Connect and sign in once (it's free). Then say “connect my Gmail” and press Allow on Google's page. I read on my own and always ask before I send anything.",
     "url": COMPOSIO_MCP, "needs": "signin"},
    {"id": "custom", "name": "Any MCP app", "about": "Paste the app's MCP address. If it supports sign-in (most new ones do, like Higgsfield or Canva), I'll open it for you; or paste a token or the command from its docs."},
]


class ConnectorError(ValueError):
    """An app's connector couldn't be reached or said no."""


# --------------------------------------------------------------- transports ---
class StdioTransport:
    def __init__(self, command, args=(), env=None, cwd=None):
        exe = shutil.which(command) or command
        if not (os.path.isabs(exe) and os.path.exists(exe)):
            hint = (" Install Node.js from nodejs.org, then try again." if command in {"npx", "node"}
                    else " Install uv from astral.sh/uv, then try again." if command in {"uv", "uvx"} else "")
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

    # -- sign in with the app ----------------------------------------------------------------
    def _json(self, url, data=None, form=False, timeout=15):
        body = None
        headers = {"Accept": "application/json", "User-Agent": "Luma/1.0"}
        if data is not None:
            body = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method="POST" if data is not None else "GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read(1_000_000) or b"{}")

    def _auth_server(self, url):
        """Where this MCP app signs people in: its protected-resource metadata, then the authorization server's."""
        parts = urllib.parse.urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        issuer = origin
        for meta in (f"{origin}/.well-known/oauth-protected-resource{parts.path.rstrip('/')}", f"{origin}/.well-known/oauth-protected-resource"):
            try:
                found = self._json(meta)
                if found.get("authorization_servers"):
                    issuer = found["authorization_servers"][0].rstrip("/")
                    break
            except Exception:
                continue
        ip = urllib.parse.urlsplit(issuer)
        for meta in (f"{ip.scheme}://{ip.netloc}/.well-known/oauth-authorization-server{ip.path}", f"{ip.scheme}://{ip.netloc}/.well-known/oauth-authorization-server",
                     f"{issuer}/.well-known/openid-configuration"):
            try:
                found = self._json(meta)
                if found.get("authorization_endpoint") and found.get("token_endpoint"):
                    return found
            except Exception:
                continue
        raise ConnectorError("That app doesn't offer a sign-in for connectors. Paste an access token from it instead.")

    def sign_in_start(self, name, url, redirect_uri, preset=None, then=None):
        """Step 1: register Luma with the app (no developer account needed), then the sign-in page to open."""
        import hashlib, secrets
        spec = next((p for p in PRESETS if p["id"] == preset), None) if preset else None
        url = (spec or {}).get("url") or str(url or "").strip()
        if not url.startswith("https://"):
            raise ConnectorError("Paste the app's MCP address (https://…).")
        meta = self._auth_server(url)
        if not meta.get("registration_endpoint"):
            raise ConnectorError("That app doesn't let new apps sign in on their own yet. Paste an access token from it instead.")
        client = self._json(meta["registration_endpoint"], {"client_name": "Luma", "redirect_uris": [redirect_uri], "grant_types": ["authorization_code", "refresh_token"],
                                                           "response_types": ["code"], "token_endpoint_auth_method": "none"})
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        state = secrets.token_urlsafe(24)
        self._signins = {k: v for k, v in getattr(self, "_signins", {}).items() if v["at"] > time.time() - 900}
        self._signins[state] = {"name": " ".join(str(name or (spec or {}).get("name") or "App").split())[:40], "url": url, "client_id": client["client_id"],
                                "token_endpoint": meta["token_endpoint"], "verifier": verifier, "redirect_uri": redirect_uri, "at": time.time(),
                                "then": then if isinstance(then, str) and re.fullmatch(r"[a-z0-9_]{2,40}", then) else None}
        query = {"response_type": "code", "client_id": client["client_id"], "redirect_uri": redirect_uri, "code_challenge": challenge,
                 "code_challenge_method": "S256", "state": state, "resource": url}
        if meta.get("scopes_supported"): query["scope"] = " ".join(meta["scopes_supported"][:12])
        return {"auth_url": meta["authorization_endpoint"] + ("&" if "?" in meta["authorization_endpoint"] else "?") + urllib.parse.urlencode(query)}

    def sign_in_finish(self, state, code):
        """Step 2: the app sent them back with a code; trade it for access, and connect."""
        pending = getattr(self, "_signins", {}).pop(str(state or ""), None)
        if not pending or pending["at"] < time.time() - 900:
            raise ConnectorError("That sign-in expired. Press Connect again.")
        tokens = self._json(pending["token_endpoint"], {"grant_type": "authorization_code", "code": code, "redirect_uri": pending["redirect_uri"],
                                                         "client_id": pending["client_id"], "code_verifier": pending["verifier"], "resource": pending["url"]}, form=True)
        if not tokens.get("access_token"):
            raise ConnectorError("The app didn't finish the sign-in. Try again.")
        added = self.add(pending["name"], url=pending["url"], token=tokens["access_token"])
        if tokens.get("refresh_token"):
            configs = self._configs()
            for c in configs:
                if c["id"] == added["id"]:
                    c.update(refresh_b64=base64.b64encode(tokens["refresh_token"].encode()).decode(), client_id=pending["client_id"],
                             token_endpoint=pending["token_endpoint"], expires=time.time() + int(tokens.get("expires_in") or 3600))
            self._save(configs)
        if pending.get("then"):
            # They asked for one app ("connect my Gmail"): go straight on to that app's own Allow page.
            try:
                added = {**added, "then_app": app_name(pending["then"]), "then_url": self.app_link(pending["then"])}
            except Exception:
                pass
        return added

    def _fresh(self, config):
        """Signed-in apps hand out access that expires: renew it quietly before connecting."""
        if not config.get("refresh_b64") or config.get("expires", 0) > time.time() + 120:
            return config
        try:
            tokens = self._json(config["token_endpoint"], {"grant_type": "refresh_token", "refresh_token": base64.b64decode(config["refresh_b64"]).decode(),
                                                            "client_id": config["client_id"], "resource": config["url"]}, form=True)
        except Exception:
            return config
        if tokens.get("access_token"):
            config = {**config, "secret_b64": base64.b64encode(tokens["access_token"].encode()).decode(), "expires": time.time() + int(tokens.get("expires_in") or 3600)}
            if tokens.get("refresh_token"): config["refresh_b64"] = base64.b64encode(tokens["refresh_token"].encode()).decode()
            self._save([config if c["id"] == config["id"] else c for c in self._configs()])
        return config

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
            config = self._fresh(config)
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
            hub = any(str(t.get("name", "")).startswith("COMPOSIO_") for t in tools)
            for tool in tools:
                if hub and HUB_HIDDEN.search(str(tool.get("name", ""))):
                    continue
                fields, kinds = fields_for(tool.get("inputSchema"))
                notes = tool.get("annotations") or {}
                luma_name = f"mcp.{config['id']}.{slug(tool['name'], 40)}"
                about = " ".join(str(tool.get("description") or tool.get("title") or tool["name"]).split())[:260]
                self._tools[luma_name] = {"connector": config["id"], "connector_name": config["name"], "tool": tool["name"],
                                          "kinds": kinds, "fields": fields, "read_only": notes.get("readOnlyHint") is True, "hub": hub,
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

    # ---- the apps hub (Composio): one sign-in, every app
    def hub(self):
        """The connected hub's id, if there is one."""
        return next((t["connector"] for t in self._tools.values() if t.get("hub") and t["tool"] == "COMPOSIO_MANAGE_CONNECTIONS"), None)

    def _hub_call(self, tool, arguments):
        hub = self.hub()
        if not hub:
            raise ConnectorError("Connect your apps first: Connectors, then Gmail & 1,500+ apps.")
        client = self._clients.get(hub)
        if not client:
            self._connect(next(c for c in self._configs() if c["id"] == hub))
            client = self._clients[hub]
        result = client.call_tool(tool, arguments)
        if result.get("isError"):
            raise ConnectorError(result_text(result)[:200] or "The apps hub said no.")
        return result_text(result)

    def app_connected(self, app):
        out = self._hub_call("COMPOSIO_MANAGE_CONNECTIONS", {"toolkits": [{"name": app, "action": "list"}]})
        return bool(re.search(r'"status"\s*:\s*"ACTIVE"', out, re.I))

    def app_link(self, app):
        """The app's own sign-in page (Google's, for Gmail), where they press Allow. None when it's already connected."""
        if self.app_connected(app):
            return None
        out = self._hub_call("COMPOSIO_MANAGE_CONNECTIONS", {"toolkits": [{"name": app, "action": "add"}]})
        url = None
        try:
            stack = [json.loads(out)]
        except ValueError:
            stack = []
        while stack and not url:
            item = stack.pop()
            if isinstance(item, dict):
                url = item.get("redirect_url") if isinstance(item.get("redirect_url"), str) else None
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
        if not url:  # not JSON, or JSON inside text
            found = re.search(r'"redirect_url"\s*:\s*"([^"]+)"', out)
            if found:
                try:
                    url = json.loads(f'"{found.group(1)}"')
                except ValueError:
                    url = found.group(1)
            else:
                plain = re.search(r"https://[^\s\"')\]]+", out)
                url = plain.group(0) if plain else None
        if not url or not str(url).startswith("https://"):
            raise ConnectorError(f"I couldn't get a sign-in link for {app_name(app)}. Try again in a minute.")
        return url

    def reads_only(self, luma_name, args):
        """Does this call only read? An app marks its read-only tools itself; through the hub, look at the actions inside the call."""
        tool = self._tools.get(luma_name) or {}
        if tool.get("read_only"):
            return True
        if not tool.get("hub"):
            return False
        name = tool["tool"]
        try:
            args = arguments_for(tool["kinds"], args or {})
        except ConnectorError:
            return False
        if name == "COMPOSIO_MANAGE_CONNECTIONS":
            kits = args.get("toolkits")
            return isinstance(kits, list) and bool(kits) and all(isinstance(k, dict) and k.get("action") == "list" for k in kits)
        if name == "COMPOSIO_MULTI_EXECUTE_TOOL":
            items = args.get("tools")
            return isinstance(items, list) and bool(items) and all(isinstance(i, dict) and only_reads(i.get("tool_slug")) for i in items)
        return only_reads(name)  # COMPOSIO_SEARCH_TOOLS, COMPOSIO_GET_TOOL_SCHEMAS: looking, not doing

    def describe(self, luma_name, args):
        """What a hub action will do, in plain words, for the approval card: {"app": "Gmail", "does": "send email", "to": …}."""
        tool = self._tools.get(luma_name) or {}
        if not tool.get("hub") or tool.get("tool") != "COMPOSIO_MULTI_EXECUTE_TOOL":
            return None
        try:
            items = arguments_for(tool["kinds"], args or {}).get("tools") or []
        except ConnectorError:
            return None
        apps, actions, details = [], [], {}
        for item in [i for i in items if isinstance(i, dict)][:3]:
            app, _, action = str(item.get("tool_slug", "")).upper().partition("_")
            apps.append(app_name(app.lower()))
            actions.append(action.replace("_", " ").lower())
            given = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
            for key, value in given.items():
                if isinstance(value, (str, int, float)) and len(details) < 6:
                    details[str(key).replace("_", " ")[:30]] = str(value)[:300]
        out = {"app": ", ".join(dict.fromkeys(a for a in apps if a)), "does": ", ".join(a for a in actions if a), **details} if apps else {}
        return out or None

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
