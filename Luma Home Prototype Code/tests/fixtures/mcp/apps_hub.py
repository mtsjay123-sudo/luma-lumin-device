"""A stand-in for Composio's hosted apps hub, for tests: the same meta-tools (search, run several actions, manage app
connections, and a remote shell Luma must never take), answering the way the hub does, in JSON text. stdio JSON-RPC."""
import json
import sys

TOOLS = [
    {"name": "COMPOSIO_SEARCH_TOOLS", "description": "Find the right app actions for a task. You have connected the apps: gmail.",
     "inputSchema": {"type": "object", "properties": {"queries": {"type": "array"}}, "required": ["queries"]}},
    {"name": "COMPOSIO_MULTI_EXECUTE_TOOL", "description": "Run one or more app actions (Gmail, Calendar, Slack...) found with search.",
     "inputSchema": {"type": "object", "properties": {"tools": {"type": "array"}, "thought": {"type": "string"}}, "required": ["tools"]}},
    {"name": "COMPOSIO_MANAGE_CONNECTIONS", "description": "List or add the user's app connections.",
     "inputSchema": {"type": "object", "properties": {"toolkits": {"type": "array"}}, "required": ["toolkits"]}},
    {"name": "COMPOSIO_REMOTE_BASH_TOOL", "description": "Run a shell command in a remote sandbox.",
     "inputSchema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
]
CONNECTED = set()


def call(name, args):
    if name == "COMPOSIO_MANAGE_CONNECTIONS":
        out = {}
        for kit in args.get("toolkits") or []:
            app = kit.get("name")
            if kit.get("action") == "add":
                out[app] = {"status": "INITIATED", "redirect_url": "https://accounts.google.com/o/oauth2/v2/auth?client=composio&app=" + app}
                CONNECTED.add(app)  # as if they pressed Allow right after
            else:
                out[app] = {"status": "ACTIVE" if app in CONNECTED else "NOT_CONNECTED"}
        return json.dumps({"successful": True, "data": {"results": out}})
    if name == "COMPOSIO_MULTI_EXECUTE_TOOL":
        results = []
        for item in args.get("tools") or []:
            slug = item.get("tool_slug")
            if slug == "GMAIL_FETCH_EMAILS":  # the fields Gmail's fetch really returns, oldest first on purpose
                query = (item.get("arguments") or {}).get("query") or ""
                mails = [{"sender": "Old Navy <deals@oldnavy.com>", "subject": "50% off everything ends tonight", "messageTimestamp": "2026-10-27T09:00:00Z",
                          "labelIds": ["INBOX", "CATEGORY_PROMOTIONS", "UNREAD"], "preview": {"body": "Shop now"}},
                         {"sender": "Sam <sam@example.com>", "subject": "Lunch Friday?", "messageTimestamp": "2026-10-27T11:48:00Z",
                          "labelIds": ["INBOX", "UNREAD", "CATEGORY_PERSONAL"], "preview": {"body": "Want to grab lunch?"}}]
                if "-category:promotions" in query:
                    mails = [m for m in mails if "CATEGORY_PROMOTIONS" not in m["labelIds"]]
                if "from:" in query:
                    who = query.split("from:", 1)[1].split()[0]
                    mails = [m for m in mails if who in m["sender"].lower().replace(" ", "")]
                data = {"messages": mails}
            else:
                data = {"done": slug, "arguments": item.get("arguments")}
            results.append({"tool_slug": slug, "response": {"successful": True, "data": data}})
        return json.dumps({"successful": True, "data": {"results": results}})
    if name == "COMPOSIO_SEARCH_TOOLS":
        return json.dumps({"tools": [{"tool_slug": "GMAIL_FETCH_EMAILS"}, {"tool_slug": "GMAIL_SEND_EMAIL"}]})
    return json.dumps({"ran": args})


def reply(msg):
    method, params = msg.get("method"), msg.get("params") or {}
    if method == "initialize":
        result = {"protocolVersion": params.get("protocolVersion"), "capabilities": {"tools": {}}, "serverInfo": {"name": "apps-hub", "version": "1"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": call(params.get("name"), params.get("arguments") or {})}]}
    else:
        return {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "Unknown method"}}
    return {"jsonrpc": "2.0", "id": msg["id"], "result": result}


for line in sys.stdin:
    msg = json.loads(line)
    if "id" in msg and "method" in msg:
        print(json.dumps(reply(msg)), flush=True)
