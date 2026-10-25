"""Games: playable prototypes from a level drawn in characters, plus a Godot 4 project of the same game.

Legend: # wall or ground, = platform, P player start, G goal, C coin, E enemy, ^ spikes, space or . empty.
The brain designs the level and the feel; this code owns the engine (physics, collisions, enemies,
pickups, lives, camera, touch controls), so every game runs. Checks fix the level's shape, make sure
the goal can be reached, and play it in a real browser: press the arrow keys and see the player move.
"""
from __future__ import annotations

import json
from collections import deque

from luma.work.studios.base import Result, Studio, check, esc, hex_color, slug, text

LEGEND = set("#=PGCE^ ")


def clean_level(rows, genre):
    """A rectangular level with one start and a goal. Raises ValueError if it can't be made playable."""
    grid = [str(r).replace(".", " ").replace("\t", " ").rstrip()[:80] for r in rows if isinstance(r, str)][:24]
    grid = ["".join(c if c in LEGEND else " " for c in r) for r in grid]
    if len(grid) < 3:
        raise ValueError("A level needs at least 3 rows.")
    width = max(8, max(len(r) for r in grid))
    grid = [list(r.ljust(width)) for r in grid]
    fixes = []
    if genre == "platformer" and not any(c == "#" for c in grid[-1]):
        grid.append(["#"] * width)
        fixes.append("added ground along the bottom")
    if genre == "topdown":
        if not all(c == "#" for c in grid[0]) or not all(c == "#" for c in grid[-1]) or not all(r[0] == "#" and r[-1] == "#" for r in grid):
            grid = [["#"] * (width + 2)] + [["#"] + r + ["#"] for r in grid] + [["#"] * (width + 2)]
            fixes.append("walled in the edges")
    starts = [(y, x) for y, r in enumerate(grid) for x, c in enumerate(r) if c == "P"]
    for y, x in starts[1:]:
        grid[y][x] = " "
    if not starts:
        spot = next(((y, x) for x in range(len(grid[0])) for y in range(len(grid) - 1) if grid[y][x] == " " and (genre == "topdown" or grid[y + 1][x] in "#=")), None)
        if not spot:
            raise ValueError("There's nowhere to put the player.")
        grid[spot[0]][spot[1]] = "P"
        fixes.append("placed the player")
    if not any(c == "G" for r in grid for c in r):
        spot = next(((y, x) for x in range(len(grid[0]) - 1, -1, -1) for y in range(len(grid) - 1) if grid[y][x] == " " and (genre == "topdown" or grid[y + 1][x] in "#=")), None)
        if not spot:
            raise ValueError("There's nowhere to put the goal.")
        grid[spot[0]][spot[1]] = "G"
        fixes.append("placed the goal")
    return ["".join(r) for r in grid], fixes


def reachable(level):
    """Top-down: can the player walk from the start to the goal without crossing walls or spikes?"""
    grid = [list(r) for r in level]
    start = next((y, x) for y, r in enumerate(grid) for x, c in enumerate(r) if c == "P")
    seen, todo = {start}, deque([start])
    while todo:
        y, x = todo.popleft()
        if grid[y][x] == "G":
            return True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]) and (ny, nx) not in seen and grid[ny][nx] not in "#^=":
                seen.add((ny, nx))
                todo.append((ny, nx))
    return False


ENGINE = r"""
const CFG = __CONFIG__;
const T = 40, cv = document.getElementById('game'), g = cv.getContext('2d');
let W = 0, H = 0; const fit = () => { W = cv.width = innerWidth; H = cv.height = innerHeight; }; addEventListener('resize', fit); fit();
let map, rows, cols, start, player, enemies, coinsLeft, score, lives, won, lost, keys = {}, tick = 0;
function load() {
  map = CFG.level.map(r => r.split('')); rows = map.length; cols = map[0].length; enemies = []; coinsLeft = 0; score = 0; lives = 3; won = lost = false;
  for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
    const c = map[y][x];
    if (c === 'P') { start = { x: x * T + 5, y: y * T + 4 }; map[y][x] = ' '; }
    if (c === 'E') { enemies.push({ x: x * T + 4, y: y * T + 8, w: T - 8, h: T - 8, vx: CFG.enemySpeed, vy: 0 }); map[y][x] = ' '; }
    if (c === 'C') coinsLeft++;
  }
  reset();
}
const reset = () => { player = { x: start.x, y: start.y, w: T - 10, h: T - 8, vx: 0, vy: 0, ground: false }; };
const solid = c => c === '#' || c === '=';
const at = (x, y) => (x < 0 || x >= cols || y < 0) ? '#' : (y >= rows ? ' ' : map[y][x]);
function collide(o, axis) {
  const x0 = Math.floor(o.x / T), x1 = Math.floor((o.x + o.w - 0.01) / T), y0 = Math.floor(o.y / T), y1 = Math.floor((o.y + o.h - 0.01) / T);
  let hit = false;
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    if (!solid(at(x, y))) continue; hit = true;
    if (axis === 'x') { if (o.vx > 0) o.x = x * T - o.w; else if (o.vx < 0) o.x = (x + 1) * T; }
    else { if (o.vy > 0) { o.y = y * T - o.h; o.ground = true; } else if (o.vy < 0) o.y = (y + 1) * T; o.vy = 0; }
  }
  return hit;
}
const overlap = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
function hurt() { lives--; if (lives <= 0) lost = true; else reset(); }
function step() {
  if (won || lost) return; tick++;
  const L = +!!(keys.ArrowLeft || keys.a), R = +!!(keys.ArrowRight || keys.d), U = +!!(keys.ArrowUp || keys.w || keys[' ']), D = +!!(keys.ArrowDown || keys.s);
  player.vx = (R - L) * CFG.speed;
  if (CFG.genre === 'topdown') player.vy = (D - U) * CFG.speed;
  else { if (U && player.ground) player.vy = -CFG.jump; player.vy = Math.min(player.vy + CFG.gravity, 15); }
  player.x += player.vx; collide(player, 'x'); player.ground = false; player.y += player.vy; collide(player, 'y');
  if (player.y > rows * T + 300) hurt();
  const x0 = Math.floor(player.x / T), x1 = Math.floor((player.x + player.w - 1) / T), y0 = Math.floor(player.y / T), y1 = Math.floor((player.y + player.h - 1) / T);
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const c = at(x, y);
    if (c === 'C') { map[y][x] = ' '; score += 10; coinsLeft--; }
    else if (c === '^') { hurt(); return; }
    else if (c === 'G') { won = true; score += 100 + lives * 50; }
  }
  for (const e of enemies) {
    e.x += e.vx; if (collide(e, 'x')) e.vx = -e.vx;
    if (CFG.genre !== 'topdown') {
      e.vy = Math.min(e.vy + CFG.gravity, 15); e.ground = false; e.y += e.vy; collide(e, 'y');
      const ahead = Math.floor((e.vx > 0 ? e.x + e.w + 1 : e.x - 1) / T), below = Math.floor((e.y + e.h + 2) / T);
      if (e.ground && !solid(at(ahead, below))) e.vx = -e.vx;
    }
    if (!e.dead && overlap(player, e)) {
      if (CFG.genre !== 'topdown' && player.vy > 0 && player.y + player.h - e.y < 16) { e.dead = true; score += 50; player.vy = -CFG.jump * 0.6; }
      else { hurt(); return; }
    }
  }
  enemies = enemies.filter(e => !e.dead);
}
function draw() {
  // Follow the player; a level smaller than the screen sits centered left-to-right and on the bottom edge.
  const camX = cols * T <= W ? (cols * T - W) / 2 : Math.max(0, Math.min(player.x - W / 2, cols * T - W));
  const camY = rows * T <= H ? rows * T - H : Math.max(0, Math.min(player.y - H / 2, rows * T - H));
  const sky = g.createLinearGradient(0, 0, 0, H); sky.addColorStop(0, CFG.sky[0]); sky.addColorStop(1, CFG.sky[1]); g.fillStyle = sky; g.fillRect(0, 0, W, H);
  g.save(); g.translate(-Math.round(camX), -Math.round(camY));
  for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
    const c = map[y][x], px = x * T, py = y * T;
    if (c === '#') { g.fillStyle = CFG.ground; g.fillRect(px, py, T, T); g.fillStyle = CFG.groundTop; if (!solid(at(x, y - 1))) g.fillRect(px, py, T, 7); }
    else if (c === '=') { g.fillStyle = CFG.groundTop; g.fillRect(px, py, T, 12); }
    else if (c === 'C') { g.fillStyle = '#FFC53D'; g.beginPath(); g.arc(px + T / 2, py + T / 2 + Math.sin((tick + x * 7) / 12) * 3, 9, 0, 7); g.fill(); }
    else if (c === '^') { g.fillStyle = '#E5484D'; g.beginPath(); for (let i = 0; i < 3; i++) { g.moveTo(px + i * T / 3, py + T); g.lineTo(px + i * T / 3 + T / 6, py + T / 2); g.lineTo(px + (i + 1) * T / 3, py + T); } g.fill(); }
    else if (c === 'G') { g.fillStyle = '#ffffff'; g.fillRect(px + 8, py - 6, 4, T + 6); g.fillStyle = CFG.accent; g.beginPath(); g.moveTo(px + 12, py - 6); g.lineTo(px + 34, py + 4); g.lineTo(px + 12, py + 14); g.fill(); }
  }
  for (const e of enemies) { g.fillStyle = CFG.enemy; g.beginPath(); g.roundRect(e.x, e.y, e.w, e.h, 8); g.fill(); g.fillStyle = '#fff'; g.fillRect(e.x + 7, e.y + 9, 6, 6); g.fillRect(e.x + e.w - 13, e.y + 9, 6, 6); }
  g.fillStyle = CFG.player; g.beginPath(); g.roundRect(player.x, player.y, player.w, player.h, 9); g.fill();
  g.fillStyle = '#fff'; const look = player.vx >= 0 ? 4 : -4; g.fillRect(player.x + 8 + look, player.y + 9, 6, 7); g.fillRect(player.x + player.w - 14 + look, player.y + 9, 6, 7);
  g.restore();
  g.fillStyle = 'rgba(0,0,0,.45)'; g.beginPath(); g.roundRect(14, 14, 290, 40, 20); g.fill();
  g.fillStyle = '#fff'; g.font = '600 18px system-ui, sans-serif'; g.fillText(`Score ${score}   Lives ${'♥'.repeat(Math.max(0, lives))}   Coins ${coinsLeft}`, 30, 41);
  if (won || lost) {
    g.fillStyle = 'rgba(0,0,0,.6)'; g.fillRect(0, 0, W, H); g.fillStyle = '#fff'; g.textAlign = 'center';
    g.font = '800 54px system-ui, sans-serif'; g.fillText(won ? CFG.winText : 'Game over', W / 2, H / 2 - 10);
    g.font = '500 22px system-ui, sans-serif'; g.fillText('Score ' + score + ' — press Enter or tap to play again', W / 2, H / 2 + 34); g.textAlign = 'left';
  }
}
addEventListener('keydown', e => { keys[e.key] = true; if ([' ', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) e.preventDefault(); if ((won || lost) && e.key === 'Enter') load(); });
addEventListener('keyup', e => { keys[e.key] = false; });
document.querySelectorAll('[data-k]').forEach(b => { const k = b.dataset.k; b.addEventListener('pointerdown', e => { e.preventDefault(); keys[k] = true; if (won || lost) load(); }); ['pointerup', 'pointerleave', 'pointercancel'].forEach(t => b.addEventListener(t, () => { keys[k] = false; })); });
cv.addEventListener('pointerdown', () => { if (won || lost) load(); });
load();
(function loop() { step(); draw(); requestAnimationFrame(loop); })();
window.__game = { state: () => ({ x: player.x, y: player.y, score, lives, won, lost, coinsLeft }), press: (k, v) => { keys[k] = v; } };
"""

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>{title}</title><style>html,body{{margin:0;height:100%;overflow:hidden;background:#000;font-family:system-ui,sans-serif}}canvas{{display:block}}
.pad{{position:fixed;bottom:18px;display:flex;gap:12px;user-select:none;-webkit-user-select:none}}.pad button{{width:64px;height:64px;border-radius:50%;border:0;background:rgba(255,255,255,.22);color:#fff;font-size:26px;backdrop-filter:blur(6px)}}
.left{{left:18px}}.right{{right:18px}}.hint{{position:fixed;top:18px;right:18px;color:#fff;opacity:.75;font-size:14px;background:rgba(0,0,0,.35);padding:8px 14px;border-radius:16px}}
@media (hover:hover){{.pad{{display:none}}}}</style></head><body><canvas id="game" aria-label="{title}"></canvas>
<div class="hint">{hint}</div><div class="pad left"><button data-k="ArrowLeft" aria-label="Left">◀</button><button data-k="ArrowRight" aria-label="Right">▶</button>{down}</div>
<div class="pad right"><button data-k="{jumpkey}" aria-label="{jumplabel}">{jumpicon}</button></div><script>{engine}</script></body></html>"""

GODOT_PROJECT = """config_version=5

[application]
config/name="{title}"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.2")

[display]
window/size/viewport_width=1280
window/size/viewport_height=720
"""

GODOT_SCENE = """[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node2D"]
script = ExtResource("1")
"""

GODOT_SCRIPT = '''extends Node2D
# Built by Luma: the same level and rules as the web version. Open this folder in Godot 4 and press Play.

const T := 40
const LEVEL := {level}
const GENRE := "{genre}"
const SPEED := {speed}
const JUMP := {jump}
const GRAVITY := {gravity}

var player: CharacterBody2D
var start := Vector2.ZERO
var score := 0
var lives := 3
var enemies: Array = []
var hud: Label
var finished := false


func _ready() -> void:
	for y in LEVEL.size():
		var row: String = LEVEL[y]
		for x in row.length():
			var c := row[x]
			var pos := Vector2(x * T + T / 2.0, y * T + T / 2.0)
			match c:
				"#", "=":
					_wall(pos)
				"P":
					start = pos
				"C":
					_area(pos, Color("#FFC53D"), "coin", 0.45)
				"G":
					_area(pos, Color("{accent}"), "goal", 0.8)
				"^":
					_area(pos, Color("#E5484D"), "spike", 0.6)
				"E":
					enemies.append({{"node": _area(pos, Color("{enemy}"), "enemy", 0.8), "origin": pos.x, "dir": 1.0}})
	player = CharacterBody2D.new()
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(T - 10, T - 8)
	shape.shape = rect
	player.add_child(shape)
	player.add_child(_box(Vector2(T - 10, T - 8), Color("{player}")))
	player.position = start
	add_child(player)
	var cam := Camera2D.new()
	player.add_child(cam)
	cam.make_current()
	var layer := CanvasLayer.new()
	hud = Label.new()
	hud.position = Vector2(16, 12)
	layer.add_child(hud)
	add_child(layer)
	_update_hud()


func _box(size: Vector2, color: Color) -> ColorRect:
	var r := ColorRect.new()
	r.size = size
	r.position = -size / 2.0
	r.color = color
	return r


func _wall(pos: Vector2) -> void:
	var body := StaticBody2D.new()
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(T, T)
	shape.shape = rect
	body.add_child(shape)
	body.add_child(_box(Vector2(T, T), Color("{ground}")))
	body.position = pos
	add_child(body)


func _area(pos: Vector2, color: Color, kind: String, scale_by: float) -> Area2D:
	var area := Area2D.new()
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(T, T) * scale_by
	shape.shape = rect
	area.add_child(shape)
	area.add_child(_box(Vector2(T, T) * scale_by, color))
	area.position = pos
	area.body_entered.connect(func(body): _touched(area, kind, body))
	add_child(area)
	return area


func _touched(area: Area2D, kind: String, body: Node) -> void:
	if body != player or finished:
		return
	match kind:
		"coin":
			score += 10
			area.queue_free()
		"goal":
			score += 100 + lives * 50
			finished = true
			hud.text = "{win_text}  Score %d" % score
			return
		"spike", "enemy":
			_hurt()
	_update_hud()


func _hurt() -> void:
	lives -= 1
	if lives <= 0:
		finished = true
		hud.text = "Game over. Score %d" % score
		return
	player.position = start
	player.velocity = Vector2.ZERO
	_update_hud()


func _update_hud() -> void:
	hud.text = "Score %d   Lives %d" % [score, lives]


func _physics_process(delta: float) -> void:
	if finished:
		return
	if GENRE == "topdown":
		player.velocity = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down") * SPEED
	else:
		player.velocity.x = Input.get_axis("ui_left", "ui_right") * SPEED
		if not player.is_on_floor():
			player.velocity.y += GRAVITY * delta
		elif Input.is_action_just_pressed("ui_accept") or Input.is_action_just_pressed("ui_up"):
			player.velocity.y = -JUMP
	player.move_and_slide()
	for e in enemies:
		var node: Area2D = e["node"]
		if not is_instance_valid(node):
			continue
		node.position.x += e["dir"] * 60.0 * delta
		if abs(node.position.x - e["origin"]) > T * 2:
			e["dir"] = -e["dir"]
	if player.position.y > LEVEL.size() * T + 400:
		_hurt()
'''


class Game(Studio):
    name, agent, title = "game", "coding", "Game"
    description = ("Design a playable game prototype. genre: platformer (run and jump) or topdown (move in four directions). goal: one line shown when you win. "
                   "player_color, accent_color: hex colors. level: 8 to 18 rows of equal length (30 to 60 characters), drawn with # wall/ground, = floating platform, "
                   "P player start (once), G goal, C coins, E enemies, ^ spikes, space for empty. Platformers need ground under the player, gaps to jump, "
                   "platforms to climb and the goal at the far right. Make it fun and fair.")
    fields = {"title": "string", "genre": "string", "goal": "text", "player_color": "text", "accent_color": "text", "level": "level"}

    def make(self, ctx, args):
        title = text(args.get("title"), 60) or "Luma Game"
        genre = "topdown" if "top" in str(args.get("genre") or "").lower() else "platformer"
        level, fixes = clean_level(args.get("level") or [], genre)
        player, accent = hex_color(args.get("player_color"), "#6E56CF"), hex_color(args.get("accent_color"), "#30A46C")
        cfg = {"title": title, "genre": genre, "level": level, "speed": 4 if genre == "platformer" else 3.4, "jump": 11.5, "gravity": 0.55, "enemySpeed": 1.4,
               "player": player, "accent": accent, "enemy": "#E5484D", "ground": "#3B3552", "groundTop": "#7C6FB0" if genre == "platformer" else "#4B4466",
               "sky": ["#1B1530", "#3A2F66"] if genre == "platformer" else ["#1A2A24", "#24382F"], "winText": text(args.get("goal"), 40) or "You win!"}
        folder = f"game/{slug(title, 'game')}"
        topdown = genre == "topdown"
        page = PAGE.format(title=esc(title), hint="Arrows or WASD to move" if topdown else "Arrows or WASD to move · Space to jump",
                           down='<button data-k="ArrowDown" aria-label="Down">▼</button>' if topdown else "",
                           jumpkey="ArrowUp" if topdown else " ", jumplabel="Up" if topdown else "Jump", jumpicon="▲",
                           engine=ENGINE.replace("__CONFIG__", json.dumps(cfg)))
        ctx.write(f"{folder}/index.html", page)
        ctx.write(f"{folder}/godot/project.godot", GODOT_PROJECT.format(title=title.replace('"', "'")))
        ctx.write(f"{folder}/godot/main.tscn", GODOT_SCENE)
        ctx.write(f"{folder}/godot/main.gd", GODOT_SCRIPT.format(level=json.dumps(level), genre=genre, speed=f"{cfg['speed'] * 60:.1f}", jump=f"{cfg['jump'] * 60:.1f}",
                                                                 gravity=f"{cfg['gravity'] * 3600:.1f}", accent=accent, enemy=cfg["enemy"], player=player,
                                                                 ground=cfg["ground"], win_text=cfg["winText"].replace('"', "'")))
        ctx.write(f"{folder}/level.txt", "\n".join(level) + "\n")
        files = [f"{folder}/index.html", f"{folder}/godot/project.godot", f"{folder}/godot/main.tscn", f"{folder}/godot/main.gd", f"{folder}/level.txt"]
        played = self.play(ctx, folder) if ctx.can_render else None
        if played and played.get("shot"):
            files.append(played["shot"])
        coins, enemies = sum(r.count("C") for r in level), sum(r.count("E") for r in level)
        return Result(files=files, summary=f"{title}: a playable {genre} ({len(level[0])}×{len(level)} level, {coins} coins, {enemies} enem{'y' if enemies == 1 else 'ies'}). "
                                           f"Open {folder}/index.html to play, or {folder}/godot in Godot 4.",
                      data={"title": title, "genre": genre, "folder": folder, "level": level, "fixes": fixes, "played": played})

    @staticmethod
    def play(ctx, folder):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return None
        report = {"errors": []}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1100, "height": 640})
                page.on("pageerror", lambda e: report["errors"].append(str(e)[:200]))
                page.goto(ctx.path(f"{folder}/index.html").as_uri())
                page.wait_for_timeout(400)
                before = page.evaluate("window.__game && window.__game.state()")
                page.keyboard.down("ArrowRight")
                page.wait_for_timeout(700)
                page.keyboard.up("ArrowRight")
                after = page.evaluate("window.__game && window.__game.state()")
                report["moved"] = bool(before and after and abs(after["x"] - before["x"]) > 4)
                report["running"] = bool(after)
                shot = f"previews/{folder.rsplit('/', 1)[-1]}-game.png"
                ctx.path(shot).parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(ctx.path(shot)))
                report["shot"] = shot
                browser.close()
        except Exception as error:
            report["unavailable"] = str(error)[:200]
        return report

    def check(self, ctx, result):
        d = result.data
        out = [check("one start and a goal", sum(r.count("P") for r in d["level"]) == 1 and any("G" in r for r in d["level"]), "The level needs exactly one P and a G.")]
        if d["genre"] == "topdown":
            out.append(check("the goal can be reached", reachable(d["level"]), "Walls or spikes block every path to the goal."))
        if d["fixes"]:
            out.append(check("level drawn cleanly", False, "Fixed: " + ", ".join(d["fixes"]), blocking=False))
        played = d.get("played")
        if played and not played.get("unavailable"):
            out.append(check("runs without errors", played.get("running") and not played["errors"], "; ".join(played["errors"][:3]) or "The game didn't start."))
            out.append(check("the player moves", played.get("moved"), "Pressing right didn't move the player."))
        else:
            out.append(check("played in a browser", False, "No browser was available, so it wasn't played.", blocking=False))
        return out
