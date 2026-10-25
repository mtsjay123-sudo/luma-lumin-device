# Luma at work: projects, studios and the terminal

Ask Luma for something big and it runs it as a **project**. It plans the work and hands each piece to a specialist
(research, data, design, documents, coding, QA). Every piece is checked the way a person would check it, and failed
checks go back to the specialist to fix. The finished files are packaged into one zip.

The blueprint's request runs end to end today:

> Research this business idea, analyze competitors, prepare the financial projections, create a 20-slide PowerPoint,
> build a branded website, generate the graphics, test the site, and package all the files for me.

It becomes six steps:

1. Research with citations.
2. A financial model in Excel, with live formulas.
3. Brand graphics.
4. A 20-slide deck with real charts.
5. A website, tested in a real browser at desktop and phone size.
6. A package of everything.

## Where you can start work

| From | How |
|---|---|
| **Luma's window** | **Projects** in the sidebar. Type what you want and press **Start**. Watch each step move, preview files, add files, add decisions, stop, pick up where it stopped, download the zip. |
| **Chat** | Just ask: *"research my taco truck idea and make a 12-slide deck and a website"*. Luma starts a project and replies right away. Ask *"how's my project going?"* any time. |
| **The terminal on this computer** | `luma work "..."` (see below). If the Luma app is open, the terminal drives it. If it isn't, Luma starts right in the terminal. |
| **Another computer, working on your Luma device** | Pair the computer once in Luma: **Settings → Your Luma device**. Then `luma work --device "..."`. The device does the work, and the finished zip lands in the folder you ran the command from. |
| **Your phone** | The paired phone sees the same projects. To be safe, it can't delete a project, and letting code run needs an extra confirm. |

All of these talk to the same projects. Something started from the terminal shows up in the window, and the reverse.

## The terminal

Luma Desktop installs the `luma` command the first time it starts:

- **Mac:** at `~/.local/bin/luma`, and puts that folder on your PATH in `~/.zshrc`. Open a new terminal window after
  the first launch.
- **Windows:** at `%APPDATA%\Luma\bin\luma.cmd`. Run it by full path, or add that folder to your PATH.

The command uses the app's own Python and settings. It never replaces a `luma` command that something else installed.

```sh
luma work "research my coffee cart idea, build the financial model and a 10-slide deck"
luma work --yes "write a python CLI that renames my photos by date, with tests"   # --yes: let code run without asking
luma work --device "make a platformer game called Moon Hop"                        # on your paired Luma device
luma work --project "Taco Rocket" "add a one-page Word summary"                    # add to an existing project

luma projects                 # every project, its state and progress
luma project "Taco Rocket"    # steps, checks, files
luma resume "Taco Rocket"     # pick up where it stopped (finished steps are kept)
luma stop "Taco Rocket"
luma approve "Taco Rocket"    # let code run in this project, and continue if it was waiting
luma usage                    # model calls, tokens and time over the last 30 days
```

While it works you see the plan, each specialist's progress, every check and the files. **Ctrl-C** stops it. Finished
steps are kept, so `luma resume` carries on from there. `luma work` exits with 0 when everything passed and 1 when a
step needs a look, so you can use it in scripts.

## What each specialist makes, and how it's checked

| Studio | Makes | Checked by |
|---|---|---|
| Research | A cited write-up (Markdown and Word) that calls out where sources disagree, with the sources saved | Sources found, more than one source, every finding cites a real source |
| Data | Analysis of your CSV, Excel or JSON files, with charts | The table was read, and the group totals add back up to the overall total |
| Financial model | An Excel workbook with live formulas, plus a yearly CSV | Opens with live formulas, assumptions aren't placeholders, the numbers make sense |
| Document | Word, PDF or Markdown | Opens in Word or as a PDF, no placeholder text, enough real content |
| Deck | An editable PowerPoint with charts, diagrams and tables | Opens in PowerPoint, slide count as asked, uses the model's numbers |
| Website | A multi-page site with brand colors and icons | Loads in a real browser at desktop and phone size, no sideways scroll, every image loads, no script errors, readable buttons |
| Graphics | Logo, icon, social post, banner, mockup and palette (SVG and PNG) | Text readable on the brand color (WCAG 4.5:1), colors distinct |
| Code | Python or Node programs with tests | Compiles, and tests pass in the sandbox. If they fail, the error goes back for up to 3 more tries |
| Game | A playable HTML5 game, plus a Godot 4 project | One start and a reachable goal, runs with no errors, and pressing right really moves the player |
| 3D | STL and OBJ meshes, OpenSCAD and Blender scripts, and a 3D viewer | The mesh has triangles and a sensible size, and the Blender script is valid. It renders when OpenSCAD or Blender is installed |
| Package | One zip with everything and a README of each deliverable and its checks | The zip opens and every file is in it |

## Safety

- **Code runs fenced in.** Only Python and Node, with a clean environment (no keys or tokens), time and size limits,
  and no installing packages. On a Mac it also runs inside Apple's sandbox: no network, writes only inside the
  project, and no reading your files. A Mac CI job checks this on every push. On other systems Luma asks once per
  project before running code.
- **Nothing leaves a project folder.** Paths with `..`, absolute paths and symlinks are refused.
- **Previews can't reach Luma.** Generated pages are shown inside a browser sandbox with a strict content policy,
  through a read-only link that's signed for that one project.
- **Deleting needs an explicit yes.** The phone can't delete at all.
- **The terminal's key** is a file only your account can read (`~/.luma/agent/cli.json`), and it's accepted only from
  this computer. Another computer reaches the device only after pairing over Luma Link, on a pinned, encrypted
  connection.
- **Nothing is sent or bought** without your yes. That rule is the same as everywhere else in Luma.

## Brains and cost

- Each step asks for the brain it needs. Light jobs stay on the local model. Heavy ones (research, writing, code) use
  the cloud brain if you've turned one on (for example Kimi K3.1 Pro with your own key). Otherwise they also stay
  local.
- Every call is counted: calls, tokens, time and errors per model per day. See it with `luma usage` or at the bottom
  of the Projects page. Set a price per model and Luma shows the cost too.

## Checking it yourself

```sh
.venv/bin/python scripts/work_eval.py             # five real projects on your local model, graded
.venv/bin/python scripts/work_eval.py --offline   # no model: proves the whole pipeline with scripted answers
```

It runs in a throwaway profile, so nothing touches your real projects. `--keep ./out` copies every project's files out
so you can open them. `--save report.json` writes the scorecard.

## Blueprint status

| Blueprint area | Status |
|---|---|
| Model gateway, routing by difficulty, usage tracking | **Built.** Local first, with an optional cloud brain per tier. |
| Execution engine: plan, track, retry, resume, approvals | **Built.** |
| Sandboxed code, files, web search and reading | **Built.** |
| PowerPoint, documents (PDF, DOCX, MD), spreadsheets (XLSX, CSV) | **Built.** |
| Websites and apps, tested in a browser | **Built.** |
| Games | **Built:** HTML5 plus a Godot export. **Not yet:** Unity and Unreal exports. |
| 3D/CAD | **Built:** STL, OBJ, OpenSCAD and Blender scripts with a viewer. **Not yet:** full Blender scenes with materials and lighting. |
| Visual media | **Built:** brand graphics as SVG and PNG. **Not yet:** an image-generation (diffusion) model. |
| Deep research with citations and conflicts | **Built.** |
| Knowledge base over your files | **Built:** keyword search (BM25) over txt, md, csv, json, html, docx, pptx, pdf and xlsx. **Next:** vector search. |
| Specialist agents and QA | **Built.** |
| Project memory: decisions every step follows | **Built.** |
| Interface: Projects page, chat, terminal, device, phone | **Built.** |
| Fine-tuning our own model | **Not yet.** It needs consented, licensed data. See `VOICE_PLAN.md`. |
