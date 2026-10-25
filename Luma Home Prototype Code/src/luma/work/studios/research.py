"""Research: search the live web, read the pages, and write up what's true, with every claim cited.

The brain only writes findings that point at numbered sources it was shown; this code checks every
citation is real, keeps the source list with links, and records where sources disagree. The owner's
own project files are searched too, and cited by file and page.
"""
from __future__ import annotations

import json
import re
from datetime import date

from luma.work.studios.base import Result, Studio, check, slug, text


class Research(Studio):
    name, agent, title = "research", "research", "Research"
    description = ("Research a question on the live web. question: what to find out. queries: 2 to 4 web searches, one per line, "
                   "that together cover it (for a business: market size, competitors and their prices, customers, trends, costs).")
    fields = {"question": "string", "queries": "text"}

    def fallback(self, ctx, task):
        return {"question": task, "queries": task}

    def make(self, ctx, args):
        question = text(args.get("question") or ctx.task, 300)
        queries = [q.strip(" -•\t") for q in re.split(r"[\n;]+", str(args.get("queries") or "")) if q.strip(" -•\t")][:4] or [question]
        sources, seen = [], set()
        for query in queries:
            ctx.progress(f"Searching: {query}")
            try:
                hits = ctx.search(query)
            except Exception as error:
                ctx.progress(f"Search didn't work for {query}: {str(error)[:120]}")
                continue
            for hit in hits or []:
                url = str(hit.get("url") or "")
                if not url.startswith("https://") or url in seen:
                    continue
                seen.add(url)
                sources.append({"id": len(sources) + 1, "title": text(hit.get("title"), 160) or url, "url": url,
                                "snippet": text(hit.get("snippet"), 500), "excerpt": text(hit.get("excerpt"), 2000)})
                if len(sources) >= 12:
                    break
        for source in sources[:6]:
            if not source["excerpt"]:
                try:
                    ctx.progress("Reading " + re.sub(r"^https://(www\.)?", "", source["url"]).split("/")[0])
                    source["excerpt"] = text(ctx.read(source["url"]), 2000)
                except Exception:
                    pass
        for hit in ctx.knowledge(question)[:3]:  # what the owner already put in the project
            sources.append({"id": len(sources) + 1, "title": f"{hit['file']} {hit['place']}".strip(), "url": "project:" + hit["file"],
                            "snippet": text(hit["text"], 500), "excerpt": text(hit["text"], 1600)})
        shown = "\n".join(f"[{s['id']}] {s['title']} ({s['url']})\n{(s['excerpt'] or s['snippet'])[:900]}" for s in sources)
        synthesis = ctx.ask(
            "Write up what these sources say about the question. Every finding must cite the numbers of the sources it comes from, "
            "and only use facts that appear in them. Put numbers in (prices, sizes, dates) when the sources give them. "
            "If sources disagree, list it under conflicts. In gaps, say what the sources didn't answer.\n"
            f"Question: {question}\n\nSources:\n{shown or '(none found)'}",
            {"summary": "text", "findings": "findings", "conflicts": "conflicts", "gaps": "text"}, "work.research_writeup") if sources else None
        valid = {s["id"] for s in sources}
        findings, conflicts = [], []
        if synthesis:
            for f in synthesis.get("findings") or []:
                cited = sorted({int(n) for n in f.get("sources") or [] if isinstance(n, (int, float)) and int(n) in valid})
                claim = text(f.get("claim"), 600)
                if claim and cited and claim.casefold() not in {x["claim"].casefold() for x in findings}:
                    findings.append({"claim": claim, "sources": cited, "confidence": f.get("confidence") if f.get("confidence") in {"high", "medium", "low"} else "medium"})
            for c in synthesis.get("conflicts") or []:
                cited = sorted({int(n) for n in c.get("sources") or [] if isinstance(n, (int, float)) and int(n) in valid})
                if text(c.get("topic")) and cited:
                    conflicts.append({"topic": text(c.get("topic"), 160), "detail": text(c.get("detail"), 600), "sources": cited})
        if not findings:  # no brain answer: the sources' own words, each cited, marked as unreviewed
            findings = [{"claim": s["snippet"] or s["excerpt"][:300], "sources": [s["id"]], "confidence": "low"} for s in sources[:8] if s["snippet"] or s["excerpt"]]
        summary = text((synthesis or {}).get("summary"), 1200) or (f"{len(findings)} findings from {len(sources)} sources." if sources else "No sources could be found.")
        gaps = text((synthesis or {}).get("gaps"), 800)
        stem = "research/" + slug(question, "research")[:40]
        report = self.markdown(question, summary, findings, conflicts, gaps, sources)
        ctx.write(stem + ".md", report)
        ctx.write(stem + "-sources.json", json.dumps([{k: s[k] for k in ("id", "title", "url")} for s in sources], indent=2))
        files = [stem + ".md", stem + "-sources.json"]
        try:
            from luma.skills import documents
            spec = documents.validate_doc(self.doc_spec(question, summary, findings, conflicts, gaps, sources))
            documents.build_docx(spec, ctx.path(stem + ".docx"))
            files.append(stem + ".docx")
        except Exception as error:
            ctx.progress(f"Couldn't make the Word version: {str(error)[:120]}")
        return Result(files=files, summary=f"Research on {question}: {summary[:400]}",
                      data={"question": question, "summary": summary, "findings": findings, "conflicts": conflicts, "gaps": gaps,
                            "sources": [{k: s[k] for k in ("id", "title", "url")} for s in sources]})

    @staticmethod
    def markdown(question, summary, findings, conflicts, gaps, sources):
        lines = [f"# {question}", "", f"_Researched {date.today():%B %d, %Y}. Every finding cites its sources._", "", "## Summary", "", summary, "", "## Findings", ""]
        lines += [f"- {f['claim']} " + "".join(f"[{n}]" for n in f["sources"]) + ("" if f["confidence"] == "high" else f" _({f['confidence']} confidence)_") for f in findings]
        if conflicts:
            lines += ["", "## Where sources disagree", ""] + [f"- **{c['topic']}**: {c['detail']} " + "".join(f"[{n}]" for n in c["sources"]) for c in conflicts]
        if gaps:
            lines += ["", "## Still unknown", "", gaps]
        lines += ["", "## Sources", ""] + [f"{s['id']}. [{s['title']}]({s['url']})" if s["url"].startswith("https://") else f"{s['id']}. {s['title']} (your project files)" for s in sources]
        return "\n".join(lines) + "\n"

    @staticmethod
    def doc_spec(question, summary, findings, conflicts, gaps, sources):
        sections = [{"heading": "Summary", "paragraphs": [summary], "bullets": []},
                    {"heading": "Findings", "paragraphs": [], "bullets": [f"{f['claim']} [{', '.join(map(str, f['sources']))}]" for f in findings][:16]}]
        if conflicts:
            sections.append({"heading": "Where sources disagree", "paragraphs": [], "bullets": [f"{c['topic']}: {c['detail']} [{', '.join(map(str, c['sources']))}]" for c in conflicts]})
        if gaps:
            sections.append({"heading": "Still unknown", "paragraphs": [gaps], "bullets": []})
        sections.append({"heading": "Sources", "paragraphs": [], "bullets": [f"[{s['id']}] {s['title']} — {s['url']}" for s in sources][:16]})
        return {"title": question[:140], "subtitle": f"Research, {date.today():%B %d, %Y}", "format": "docx", "sections": sections}

    def check(self, ctx, result):
        d = result.data
        sources, findings = d.get("sources", []), d.get("findings", [])
        ids = {s["id"] for s in sources}
        return [
            check("found sources", sources, "No sources could be found online or in the project."),
            check("more than one source", len({s["url"] for s in sources}) >= 2, f"Only {len(sources)} source(s); conclusions rest on one place.", blocking=False),
            check("every finding is cited", findings and all(f["sources"] and set(f["sources"]) <= ids for f in findings), "A finding cites a source that wasn't read."),
            check("written up", all(ctx.exists(f) for f in result.files), "The report file is missing."),
        ]
