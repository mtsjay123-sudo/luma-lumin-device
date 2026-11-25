"""The brain contest: which open brain is best for Luma, measured with Luma's own tests.

The owner, Nov 25: "if we need to make our own model we will do so by breaking down the best open source model, taking
it and making ours how Luma needs to be. Find the very best open source." Blogs rank models on tests that aren't about
being someone's friend. So each candidate is fetched on GitHub's machines (Hugging Face can't be reached from the cloud
sandbox), its license is read from its maker's own page first (rule 7: MIT, Apache-2.0 or BSD, or it isn't run), and it
answers the safety net and the conversations of Human Test v2 through Luma's whole layer, beside the brain Luma uses
today.

    python -I scripts/brain_contest.py find --official Qwen/Qwen3.5-4B --gguf unsloth/Qwen3.5-4B-GGUF,bartowski/Qwen_Qwen3.5-4B-GGUF

prints the license and the file to fetch, and writes BRAIN_URL, BRAIN_FILE and BRAIN_LICENSE where a workflow reads
them. Nothing is downloaded by this script: the workflow fetches the one file into a folder of its own (rule 9).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://huggingface.co/api/models/"
ALLOWED = ("mit", "apache-2.0", "bsd", "bsd-2-clause", "bsd-3-clause", "bsd-3-clause-clear")
QUANTS = ("Q4_K_M", "Q4_0")


class Refused(Exception):
    """A candidate that isn't run, and why."""


def license_of(info):
    """The license a model's page states, lower case: from its card first, then its tags. "" when it states none."""
    card = info.get("cardData") or {}
    stated = card.get("license")
    if isinstance(stated, list):
        stated = stated[0] if stated else ""
    stated = str(stated or "").strip().lower()
    if stated == "other":
        return "other: " + str(card.get("license_name") or card.get("license_link") or "its own terms").strip().lower()
    if stated:
        return stated
    for tag in info.get("tags") or []:
        if str(tag).lower().startswith("license:"):
            return str(tag).split(":", 1)[1].strip().lower()
    return ""


def allowed(stated):
    return stated in ALLOWED


def pick(names, quants=QUANTS):
    """The one file to fetch: the first quant on the list that the copy has, whole (not split in pieces), never the
    picture half of a model that also sees."""
    whole = [n for n in names if n.lower().endswith(".gguf") and "-of-" not in n and "mmproj" not in n.lower() and "/" not in n]
    for quant in quants:
        fits = sorted((n for n in whole if quant.lower() in n.lower()), key=len)
        if fits:
            return fits[0]
    return None


def fetch(repo):
    request = urllib.request.Request(API + repo, headers={"User-Agent": "luma-brain-contest"})
    with urllib.request.urlopen(request, timeout=60) as answer:
        return json.load(answer)


def find(official, copies, quants=QUANTS, fetch=fetch):
    """What to run for one candidate: {"license", "from", "repo", "file", "url"}. Raises Refused when the maker's page
    states a license that isn't allowed, states none anywhere, or no copy has a file to run."""
    where = "the maker's page"
    try:
        stated = license_of(fetch(official))
    except Exception as error:  # a page that needs a sign-in, or a name a blog got wrong
        stated, where = "", f"a copy's page (the maker's couldn't be read: {type(error).__name__})"
    found = None
    for repo in copies:
        try:
            info = fetch(repo)
        except Exception:
            continue
        name = pick([s.get("rfilename", "") for s in info.get("siblings") or []], quants)
        if not stated:
            stated = license_of(info)
        if name and not found:
            found = (repo, name)
    if not stated:
        raise Refused(f"{official}: no license is stated on its page or on any copy's. Not run.")
    if not allowed(stated):
        raise Refused(f"{official}: its license is \"{stated}\" (read from {where}). Rule 7 allows MIT, Apache-2.0 and BSD. Not run.")
    if not found:
        raise Refused(f"{official}: none of {', '.join(copies)} has a whole {' or '.join(quants)} file. Not run.")
    repo, name = found
    return {"license": stated, "from": where, "repo": repo, "file": name, "url": f"https://huggingface.co/{repo}/resolve/main/{name}"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="what", required=True)
    one = sub.add_parser("find")
    one.add_argument("--official", required=True)
    one.add_argument("--gguf", required=True)
    one.add_argument("--quant", default=",".join(QUANTS))
    args = parser.parse_args(argv)
    try:
        got = find(args.official, [r.strip() for r in args.gguf.split(",") if r.strip()], tuple(q.strip() for q in args.quant.split(",") if q.strip()))
    except Refused as why:
        print(why)
        return 3
    print(f"{args.official}: license {got['license']} (read from {got['from']}). File: {got['repo']} / {got['file']}")
    out = os.environ.get("GITHUB_ENV")
    if out:
        with open(out, "a", encoding="utf-8") as handle:
            handle.write(f"BRAIN_URL={got['url']}\nBRAIN_FILE={got['file']}\nBRAIN_LICENSE={got['license']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
