"""Refresh Google Scholar citation counts in the CV bibliography.

Fetches the citation count of every paper on the Google Scholar profile, matches
them to the bib entries by title, and then:

  * stars the ``--top N`` most cited entries via ``keywords = {...,citation}``
  * records the count in ``note = {N citations}`` on those entries
  * updates the h-index sentence in cv_duarte_javier.tex

Only the affected lines are rewritten, so the diff stays small.

Backends (``--backend``):

  scholarly  free scraper, ``pip install scholarly`` (Google blocks it eventually)
  serpapi    paid but reliable, needs SERPAPI_KEY in the environment
  cache      re-use the last fetch in scholar_cache.json, no network

Typical use::

    python update_scholar_citations.py --dry-run
    python update_scholar_citations.py
"""

import argparse
import bisect
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

SCHOLAR_ID = "GTtW9H0AAAAJ"
CACHE_FILE = "scholar_cache.json"
LOOKUP_CACHE_FILE = "scholar_lookups.json"
OVERRIDES_FILE = "scholar_overrides.json"
CV_TEX = "cv_duarte_javier.tex"

# Scholar resolves a single paper from an arXiv id or DOI, which beats title
# matching outright. It is heavily rate limited, so results are cached forever
# and only entries the profile scrape could not place are ever looked up.
LOOKUP_URL = "https://scholar.google.com/scholar_lookup"
LOOKUP_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
# Every page ships a hidden "can't perform the operation" div and a Cite dialog
# carrying data-cid, so neither is usable as a signal. Only a real result block
# has class="gs_r gs_or ...".
RESULT_RE = re.compile(r'class="gs_r gs_or')

# Scholar blocks a chatty IP for far longer than any backoff is worth waiting
# out, so bail after this many consecutive empty answers rather than grinding.
GIVE_UP_AFTER = 3
CITED_RE = re.compile(r"Cited by (\d+)")
TITLE_RE = re.compile(r'<h3 class="gs_rt".*?</h3>', re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")

BIB_FILES = [
    "bib_publications.bib",
    "bib_reviews.bib",
    "bib_bookchapters.bib",
    "bib_refproceedings.bib",
    "bib_proceedings.bib",
    "bib_other.bib",
    "bib_workinprogress.bib",
]

ENTRY_RE = re.compile(r"^@(\w+)\s*\{\s*([^,\s]+)\s*,")
FIELD_RE = re.compile(r"^(?P<indent>\s+)(?P<name>[A-Za-z]+)(?P<pad>\s*)=\s*(?P<value>.*?),?\s*$")
HINDEX_RE = re.compile(r"(h-index according to Google Scholar is\s+)(\d+)")

# Scholar truncates long titles in the profile listing with an ellipsis.
TRUNCATION = ("…", "...")

# Words shared by more entries than this are too common to narrow a fuzzy search.
MAX_BUCKET = 200

# LaTeX the CV uses in titles, spelled the way Google Scholar renders it.
MACROS = {
    r"\Pp": "p", r"\PH": "H", r"\PW": "W", r"\PZ": "Z", r"\Pe": "e",
    r"\PQb": "b", r"\PQc": "c", r"\PQt": "t", r"\Pgm": "mu", r"\Pgg": "gamma",
    r"\bbbar": "bb", r"\ccbar": "cc", r"\ttbar": "tt", r"\qqbar": "qq",
    r"\TeV": " TeV", r"\GeV": " GeV", r"\MeV": " MeV", r"\fbinv": " fb-1",
    r"\pt": " pT", r"\sqrt": " sqrt", r"\unit": " ", r"\mathrm": " ",
    r"\text": " ", r"\ensuremath": " ", r"\abs": " ", r"\left": " ", r"\right": " ",
}

# Scholar spells these out where the CV abbreviates them, or the reverse. Both
# spellings collapse onto the same token, so either direction matches.
ACRONYMS = [
    (r"field[- ]programmable gate arrays?|fpgas?", "fpga"),
    (r"large hadron collider|lhc", "lhc"),
    (r"application[- ]specific integrated circuits?|asics?", "asic"),
    (r"graph neural networks?|gnns?", "gnn"),
    (r"deep neural networks?|dnns?", "dnn"),
    (r"convolutional neural networks?|cnns?", "cnn"),
    (r"generative adversarial networks?|gans?", "gan"),
    (r"machine learning|\bml\b", "machinelearning"),
    (r"artificial intelligence|\bai\b", "artificialintelligence"),
    (r"high energy physics|\bhep\b", "highenergyphysics"),
    (r"transverse momentum|\bpt\b", "pt"),
    (r"proton[- ]proton|\bpp\b", "pp"),
]
ACRONYMS = [(re.compile(pattern), token) for pattern, token in ACRONYMS]


# ---------------------------------------------------------------------------
# fetching
# ---------------------------------------------------------------------------


def fetch_scholarly(scholar_id, use_proxy=False):
    """Scrape the profile with the `scholarly` package."""
    try:
        from scholarly import ProxyGenerator, scholarly
    except ImportError:
        sys.exit("scholarly is not installed: pip install scholarly")

    if use_proxy:
        pg = ProxyGenerator()
        if not pg.FreeProxies():
            sys.exit("could not set up a free proxy pool")
        scholarly.use_proxy(pg)

    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=["basics", "indices", "publications"])

    pubs = []
    for pub in author.get("publications", []):
        bib = pub.get("bib", {})
        pubs.append(
            {
                "title": bib.get("title", ""),
                "year": str(bib.get("pub_year", "")),
                "citations": int(pub.get("num_citations", 0) or 0),
            }
        )
    return {
        "scholar_id": scholar_id,
        "fetched": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hindex": int(author.get("hindex", 0) or 0),
        "citedby": int(author.get("citedby", 0) or 0),
        "publications": pubs,
    }


def fetch_serpapi(scholar_id, api_key):
    """Read the profile through the SerpAPI Google Scholar Author endpoint."""
    pubs = []
    hindex = 0
    citedby = 0
    start = 0
    while True:
        params = {
            "engine": "google_scholar_author",
            "author_id": scholar_id,
            "api_key": api_key,
            "num": 100,
            "start": start,
            "sort": "cited_by",
        }
        url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.load(response)

        if "error" in payload:
            sys.exit("SerpAPI error: {}".format(payload["error"]))

        for row in payload.get("cited_by", {}).get("table", []):
            if "h_index" in row:
                hindex = int(row["h_index"]["all"])
            if "citations" in row:
                citedby = int(row["citations"]["all"])

        articles = payload.get("articles", [])
        for article in articles:
            pubs.append(
                {
                    "title": article.get("title", ""),
                    "year": str(article.get("year", "")),
                    "citations": int(article.get("cited_by", {}).get("value", 0) or 0),
                }
            )
        if len(articles) < 100:
            break
        start += 100
        time.sleep(1)

    return {
        "scholar_id": scholar_id,
        "fetched": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hindex": hindex,
        "citedby": citedby,
        "publications": pubs,
    }


# ---------------------------------------------------------------------------
# single-paper lookup by arXiv id
# ---------------------------------------------------------------------------


def scholar_lookup(param, value, delay=20, attempts=4):
    """Resolve one paper on Scholar. Returns ``(title, citations)`` or None.

    Scholar throttles a burst of these by serving a page with no result block
    rather than a CAPTCHA, which is byte-for-byte how it reports an unknown
    identifier too. Retrying is the only way to tell the two apart.
    """
    query = urllib.parse.urlencode({param: value})
    request = urllib.request.Request(LOOKUP_URL + "?" + query, headers={"User-Agent": LOOKUP_UA})
    wait = delay
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                html = response.read().decode("utf-8", "replace")
        except Exception as error:  # transient network or HTTP error
            print("    {}={} request failed ({}), waiting {}s".format(param, value, error, wait))
            time.sleep(wait)
            wait *= 2
            continue

        if RESULT_RE.search(html):
            cited = CITED_RE.search(html)
            title = TITLE_RE.search(html)
            title = TAG_RE.sub("", title.group(0)).strip() if title else ""
            if not title and not cited:
                return None  # a block with nothing in it is not an answer
            return title, int(cited.group(1)) if cited else 0

        # No result block means either no such record or backpressure, and the
        # two are indistinguishable in the markup. Retry before believing it.
        if attempt == attempts - 1:
            return None
        print("    no result for {}={}, retrying in {}s".format(param, value, wait))
        time.sleep(wait)
        wait *= 2
    return None


def resolve_missing(needed, by_key, lookups, delay, limit):
    """Fill in counts for entries the profile scrape could not place."""
    def identifiers(key):
        # scholar_lookup understands arxiv_id but not doi -- a doi= query returns
        # a page with no result block at all, so there is nothing to fall back to.
        value = by_key[key]["fields"].get("eprint", {}).get("value", "").strip()
        if value:
            yield "arxiv_id", value, "arxiv_id:{}".format(value)

    resolved = {}

    def take(key, param, value, hit):
        if hit:
            resolved[key] = (hit["citations"], "{}={}".format(param, value), hit["title"])
            return True
        return False

    # Cached answers cost nothing, so apply all of them before spending budget.
    remaining = []
    for key in needed:
        if not any(take(key, param, value, lookups[cache_key])
                   for param, value, cache_key in identifiers(key) if cache_key in lookups):
            remaining.append(key)

    budget = limit
    misses = 0
    for key in remaining:
        for param, value, cache_key in identifiers(key):
            if cache_key in lookups:
                continue
            if budget <= 0:
                print("  lookup budget spent; {} entries still unresolved "
                      "(raise --lookup-limit)".format(len(remaining) - len(resolved)))
                return resolved
            budget -= 1
            print("  looking up {} via {}={}".format(key, param, value))
            found = scholar_lookup(param, value, delay=delay)
            # Only cache hits. A miss is indistinguishable from throttling, and
            # caching it would poison every later run with a permanent zero.
            if found:
                lookups[cache_key] = {"title": found[0], "citations": found[1]}
                misses = 0
                take(key, param, value, lookups[cache_key])
                break
            misses += 1
            if misses >= GIVE_UP_AFTER:
                print("  {} lookups in a row came back empty -- Scholar has almost certainly\n"
                      "  blocked this IP. The block lasts far longer than a backoff can wait;\n"
                      "  retry in an hour or use --backend serpapi.".format(misses))
                return resolved
            time.sleep(delay)
    return resolved


# ---------------------------------------------------------------------------
# title matching
# ---------------------------------------------------------------------------


def normalize(title):
    """Reduce a LaTeX or Scholar title to comparable lowercase alphanumerics.

    Beam energies matter here: ``$\\sqrt{s} = 13\\TeV$`` and ``7\\TeV`` are often
    the only thing separating two otherwise identical CMS titles, so the numbers
    and units inside math have to survive.
    """
    text = unicodedata.normalize("NFKD", title)
    for macro, plain in MACROS.items():
        text = text.replace(macro, plain)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)  # any macro we do not know about
    text = re.sub(r"[${}~^_\\]", " ", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    text = " ".join(text.split())
    for pattern, token in ACRONYMS:
        text = pattern.sub(token, text)
    return " ".join(text.split())


def numbers(norm):
    """The standalone numbers in a title -- a strong discriminator for HEP."""
    return {w for w in norm.split() if w.isdigit()}


def is_duplicate_record(title):
    """Scholar splits some papers into stub records that carry no citations."""
    lowered = title.strip().lower()
    return lowered.startswith(("author correction:", "erratum:", "correction:", "publisher correction:", "arxiv:"))


def match_titles(scholar_pubs, entries, overrides=None, threshold=0.87):
    """Map bib keys to Scholar citation counts and how they were matched.

    Tries an exact normalized match, then a prefix match for the titles Scholar
    truncates, then a guarded fuzzy ratio. Returns ``(counts, how)`` where
    ``how[key]`` records the match method and the Scholar title behind it, so
    every number that lands in the CV can be traced back.
    """
    overrides = overrides or {}
    by_norm = {}
    by_token = {}
    for entry in entries:
        norm = normalize(entry["title"])
        by_norm.setdefault(norm, []).append(entry)
        for token in set(norm.split()):
            by_token.setdefault(token, set()).add(norm)

    forced = {normalize(title): key for key, title in overrides.items() if title}
    prefixes = sorted(by_norm)
    by_key = {e["key"]: e for e in entries}
    counts = {}
    how = {}

    def record(key, pub, method):
        if counts.get(key, -1) < pub["citations"]:
            counts[key] = pub["citations"]
            how[key] = (method, pub["title"])
        counts.setdefault(key, pub["citations"])

    for pub in scholar_pubs:
        raw = pub["title"]
        norm = normalize(raw)
        if not norm or is_duplicate_record(raw):
            continue

        if norm in forced:
            record(forced[norm], pub, "override")
            continue

        hits = by_norm.get(norm)
        method = "exact"

        if not hits and raw.rstrip().endswith(TRUNCATION):
            start = bisect.bisect_left(prefixes, norm)
            hits = [e for n in prefixes[start:] if n.startswith(norm) for e in by_norm[n]]
            method = "prefix"

        if not hits:
            # Only compare against titles sharing a rare word, otherwise this is
            # a 10^6-way SequenceMatcher sweep on a profile this size.
            candidates = set()
            for token in set(norm.split()):
                bucket = by_token.get(token)
                if bucket and len(bucket) <= MAX_BUCKET:
                    candidates.update(bucket)
            pub_numbers = numbers(norm)
            best, best_ratio = None, 0.0
            matcher = SequenceMatcher(None, norm, "")
            for candidate in candidates:
                # 7 TeV and 13 TeV papers share almost every word; never let a
                # fuzzy score bridge a disagreement about the numbers. Scholar
                # often renders the energy away entirely ("in pp collisions at "),
                # so only veto when both sides actually state a number.
                candidate_numbers = numbers(candidate)
                if pub_numbers and candidate_numbers and candidate_numbers != pub_numbers:
                    continue
                matcher.set_seq2(candidate)
                if matcher.real_quick_ratio() < threshold or matcher.quick_ratio() < threshold:
                    continue
                ratio = matcher.ratio()
                if ratio > best_ratio:
                    best, best_ratio = by_norm[candidate], ratio
            if best_ratio >= threshold:
                hits, method = best, "fuzzy {:.2f}".format(best_ratio)

        if not hits:
            continue

        # A paper can appear on the profile more than once (arXiv + journal).
        for entry in hits:
            if overrides.get(entry["key"], "") is None:
                continue  # explicitly pinned to "do not match"
            record(entry["key"], pub, method)

    for key, title in overrides.items():
        if title and key in by_key and key not in counts:
            print("warning: override for {} matched no Scholar record: {!r}".format(key, title))

    return counts, how


# ---------------------------------------------------------------------------
# bib parsing and rewriting
# ---------------------------------------------------------------------------


def parse_bib(path):
    """Return the file's lines plus a light structural index of each entry."""
    with open(path, encoding="utf-8") as bib_file:
        lines = bib_file.read().split("\n")

    entries = []
    current = None
    for lineno, line in enumerate(lines):
        entry_match = ENTRY_RE.match(line)
        if entry_match:
            if entry_match.group(1).lower() == "comment":
                current = None
                continue
            current = {
                "file": path,
                "key": entry_match.group(2),
                "start": lineno,
                "end": None,
                "fields": {},
                "repeats": {},
                "title": "",
            }
            entries.append(current)
            continue

        if current is None:
            continue

        if line.strip() == "}":
            current["end"] = lineno
            current = None
            continue

        field_match = FIELD_RE.match(line)
        if field_match:
            name = field_match.group("name").lower()
            value = field_match.group("value").strip()
            if value.startswith("{") and value.endswith("}"):
                value = value[1:-1]
            occurrence = {
                "lineno": lineno,
                "value": value,
                "indent": field_match.group("indent"),
                "column": len(field_match.group("indent")) + len(field_match.group("name")) + len(field_match.group("pad")),
            }
            current["fields"].setdefault(name, occurrence)
            current["repeats"].setdefault(name, []).append(occurrence)
            if name == "title":
                current["title"] = value

    return lines, [e for e in entries if e["end"] is not None]


def field_line(entry, name, value):
    """Format a field line using the entry's own ``=`` alignment."""
    sample = next(iter(entry["fields"].values()), None)
    indent = sample["indent"] if sample else "  "
    column = sample["column"] if sample else len(name)
    pad = " " * max(1, column - len(indent) - len(name))
    return "{}{}{}= {{{}}},".format(indent, name, pad, value)


def set_field(entry, edits, name, value):
    """Queue an update, or an alphabetically placed insertion, for one field."""
    if name in entry["fields"]:
        field = entry["fields"][name]
        if field["value"] == value:
            return False
        line = entry["fields"][name]
        indent = line["indent"]
        pad = " " * max(1, line["column"] - len(indent) - len(name))
        edits["replace"][(entry["file"], line["lineno"])] = "{}{}{}= {{{}}},".format(indent, name, pad, value)
        return True

    after = entry["start"]
    for existing, field in sorted(entry["fields"].items()):
        if existing < name:
            after = max(after, field["lineno"])
    edits["insert"].setdefault((entry["file"], after), []).append(field_line(entry, name, value))
    return True


# A note may carry an errata link before the count:
#   note = {[Erratum: \doi{10.1016/j.physletb.2017.09.029}], 359 citations}
COUNT_NOTE_RE = re.compile(r"^(?P<prefix>.*?)(?P<count>\d+)\s+citations$", re.DOTALL)


def citation_note(entry):
    """The ``note`` holding a citation count, plus its non-count prefix.

    ``note`` is also used for errata links, and biber honours only the last one
    of a repeated field, so a blind insert silently deletes the erratum.
    """
    for occurrence in entry["repeats"].get("note", []):
        match = COUNT_NOTE_RE.match(occurrence["value"].replace("\t", " ").strip())
        if match:
            return occurrence, match.group("prefix")
    return None, ""


def set_citation_note(entry, edits, count):
    """Update the count in place, keeping any errata prefix; report conflicts."""
    occurrence, prefix = citation_note(entry)
    if occurrence is not None:
        value = "{}{} citations".format(prefix, count)
        if occurrence["value"] == value:
            return None
        indent = occurrence["indent"]
        pad = " " * max(1, occurrence["column"] - len(indent) - len("note"))
        edits["replace"][(entry["file"], occurrence["lineno"])] = "{}note{}= {{{}}},".format(indent, pad, value)
        return None
    if entry["repeats"].get("note"):
        return entry["key"]  # a note with no count in it; leave it alone
    set_field(entry, edits, "note", "{} citations".format(count))
    return None


def recorded_count(entry):
    """The citation count already written in the bib, if any.

    Must not just grab the first number in the field: a note can read
    ``[Corrigendum: \\DOI{10.1038/s41586-023-06164-8}], 1321 citations``.
    """
    occurrence, _ = citation_note(entry)
    if occurrence is None:
        return None
    return int(COUNT_NOTE_RE.match(occurrence["value"].replace("\t", " ").strip()).group("count"))


def drop_citation_note(entry, edits):
    """Remove the count, keeping the line if it also carries an errata link."""
    occurrence, prefix = citation_note(entry)
    if occurrence is None:
        return
    prefix = prefix.rstrip().rstrip(",")
    if prefix:
        indent = occurrence["indent"]
        pad = " " * max(1, occurrence["column"] - len(indent) - len("note"))
        edits["replace"][(entry["file"], occurrence["lineno"])] = "{}note{}= {{{}}},".format(indent, pad, prefix)
    else:
        edits["delete"].add((entry["file"], occurrence["lineno"]))


def drop_field(entry, edits, name):
    if name not in entry["fields"]:
        return False
    edits["delete"].add((entry["file"], entry["fields"][name]["lineno"]))
    return True


def apply_edits(path, lines, edits):
    out = []
    for lineno, line in enumerate(lines):
        if (path, lineno) in edits["delete"]:
            continue
        out.append(edits["replace"].get((path, lineno), line))
        out.extend(edits["insert"].get((path, lineno), []))
    with open(path, "w", encoding="utf-8") as bib_file:
        bib_file.write("\n".join(out))


# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", choices=["scholarly", "serpapi", "cache"], default="scholarly")
    parser.add_argument("--scholar-id", default=SCHOLAR_ID)
    parser.add_argument("--top", type=int, default=15, help="number of entries to star (default: 15)")
    parser.add_argument("--pool", choices=["career", "all"], default="career",
                        help="rank only entries printed in the CV (career) or every entry")
    parser.add_argument("--proxy", action="store_true", help="route the scholarly backend through free proxies")
    parser.add_argument("--cache-file", default=CACHE_FILE)
    parser.add_argument("--overrides", default=OVERRIDES_FILE,
                        help="JSON of bib key -> exact Scholar title (null to ignore an entry)")
    parser.add_argument("--lookup", action="store_true",
                        help="resolve unmatched entries by arXiv id / DOI (slow, rate limited, cached)")
    parser.add_argument("--lookup-cache", default=LOOKUP_CACHE_FILE)
    parser.add_argument("--lookup-delay", type=float, default=20.0, help="seconds between lookups (default: 20)")
    parser.add_argument("--lookup-limit", type=int, default=25, help="max new lookups per run (default: 25)")
    parser.add_argument("--force", action="store_true", help="unstar entries even if their match looks broken")
    parser.add_argument("-n", "--dry-run", action="store_true", help="report changes without writing")
    args = parser.parse_args()

    # ---- 1. get the Scholar data -------------------------------------------
    if args.backend == "cache":
        if not os.path.exists(args.cache_file):
            sys.exit("no cache at {}; run with --backend scholarly or serpapi first".format(args.cache_file))
        with open(args.cache_file, encoding="utf-8") as cache_file:
            data = json.load(cache_file)
        print("using cached fetch from {}".format(data.get("fetched", "?")))
    elif args.backend == "serpapi":
        api_key = os.environ.get("SERPAPI_KEY")
        if not api_key:
            sys.exit("set SERPAPI_KEY in the environment")
        data = fetch_serpapi(args.scholar_id, api_key)
    else:
        data = fetch_scholarly(args.scholar_id, use_proxy=args.proxy)

    if args.backend != "cache":
        with open(args.cache_file, "w", encoding="utf-8") as cache_file:
            json.dump(data, cache_file, indent=2, ensure_ascii=False)
        print("fetched {} publications, h-index {}".format(len(data["publications"]), data["hindex"]))

    # ---- 2. read the bibliography ------------------------------------------
    files = {}
    entries = []
    for path in BIB_FILES:
        if not os.path.exists(path):
            continue
        lines, parsed = parse_bib(path)
        files[path] = lines
        entries.extend(parsed)
    print("read {} entries from {} bib files".format(len(entries), len(files)))

    # ---- 3. match ----------------------------------------------------------
    overrides = {}
    if os.path.exists(args.overrides):
        with open(args.overrides, encoding="utf-8") as override_file:
            overrides = json.load(override_file)
        print("loaded {} manual overrides from {}".format(len(overrides), args.overrides))

    counts, how = match_titles(data["publications"], entries, overrides)
    print("matched {} entries to the Scholar profile".format(len(counts)))

    by_key = {e["key"]: e for e in entries}

    def is_career(entry):
        return "career" in entry["fields"].get("keywords", {}).get("value", "")

    # ---- 3b. rescue entries the title match could not place ----------------
    # Scholar splits some papers into stub records that never surface on the
    # profile listing, so resolve those few by arXiv id or DOI instead.
    if args.lookup:
        lookups = {}
        if os.path.exists(args.lookup_cache):
            with open(args.lookup_cache, encoding="utf-8") as lookup_file:
                lookups = json.load(lookup_file)

        needed = []
        for entry in entries:
            key = entry["key"]
            if args.pool == "career" and not is_career(entry):
                continue
            was_starred = "citation" in entry["fields"].get("keywords", {}).get("value", "")
            before = recorded_count(entry) or 0
            now = counts.get(key)
            # A zero on a brand-new paper is just true, so only chase a zero when
            # the entry used to be a top cite and has apparently collapsed.
            if now is None or (was_starred and before and now < 0.5 * before):
                needed.append(key)

        if needed:
            print("\nresolving {} unplaced entries by identifier "
                  "(~{}s each, cached in {})".format(len(needed), args.lookup_delay, args.lookup_cache))
            try:
                resolved = resolve_missing(needed, by_key, lookups, args.lookup_delay, args.lookup_limit)
            finally:
                with open(args.lookup_cache, "w", encoding="utf-8") as lookup_file:
                    json.dump(lookups, lookup_file, indent=2, ensure_ascii=False, sort_keys=True)
            for key, (count, via, title) in resolved.items():
                if count > counts.get(key, 0):
                    counts[key] = count
                    how[key] = ("lookup {}".format(via), title)
            print("  resolved {} of {}".format(len(resolved), len(needed)))

    # A null override pins an entry: Scholar has no usable record for it, so keep
    # whatever the bib already says and leave it starred.
    pinned = {k for k, title in overrides.items() if title is None and k in by_key}
    for key in pinned:
        counts[key] = recorded_count(by_key[key]) or 0
        how[key] = ("pinned", "")

    pool = [k for k in counts if args.pool == "all" or is_career(by_key[k])]
    pool.sort(key=lambda k: (-counts[k], k))
    starred = set(pool[: args.top]) | pinned

    # A paper Scholar has split across stub records looks like a paper that lost
    # all its citations. Refuse to unstar on that basis without a look.
    previously = {e["key"] for e in entries if "citation" in e["fields"].get("keywords", {}).get("value", "")}
    suspect = []
    for key in previously - starred:
        before = recorded_count(by_key[key]) or 0
        now = counts.get(key)
        # Counts drift down a little when Scholar re-indexes; that is normal.
        # Vanishing entirely, or halving, means the match broke.
        if now is None or now == 0 or (before and now < 0.5 * before):
            suspect.append((key, before, now))
    if suspect:
        print("\nWARNING: these starred entries lost ground; Scholar fragments records,")
        print("so check them on the profile before accepting the drop:")
        for key, before, now in sorted(suspect):
            print("  {:22s} bib says {:>5}, Scholar now {}".format(key, before, "no match" if now is None else now))
        print("  pin the right record in {} to fix, e.g. {{\"{}\": \"exact Scholar title\"}}".format(
            args.overrides, suspect[0][0]))
        if not args.force and not args.dry_run:
            sys.exit("\nrefusing to unstar without --force")

    # ---- 4. rewrite the bib files ------------------------------------------
    edits = {"replace": {}, "insert": {}, "delete": set()}
    added, removed, conflicts = [], [], []

    repeated = [(e["key"], name) for e in entries for name, occ in e["repeats"].items() if len(occ) > 1]
    if repeated:
        print("\nWARNING: repeated fields, biber keeps only the last one:")
        for key, name in repeated:
            print("  {} has {} '{}' fields".format(key, len(by_key[key]["repeats"][name]), name))

    for entry in entries:
        key = entry["key"]
        keywords = entry["fields"].get("keywords", {}).get("value", "")
        tags = [t.strip() for t in keywords.split(",") if t.strip()]
        was_starred = "citation" in tags

        if key in starred:
            if not was_starred:
                tags.append("citation")
                added.append(key)
            conflict = set_citation_note(entry, edits, counts[key])
            if conflict:
                conflicts.append((conflict, counts[key]))
        elif was_starred:
            tags.remove("citation")
            removed.append(key)
            drop_citation_note(entry, edits)

        wanted = ",".join(tags)  # keep the original order, citation goes last
        if wanted != keywords:
            if wanted:
                set_field(entry, edits, "keywords", wanted)
            else:
                drop_field(entry, edits, "keywords")

    # ---- 5. report ---------------------------------------------------------
    print("\ntop {} by Google Scholar citations ({} pool):".format(args.top, args.pool))
    for rank, key in enumerate(pool[: args.top], 1):
        method, title = how.get(key, ("?", ""))
        flag = " NEW" if key in added else ""
        print("  {:2d}. {:6d}  {:22s} [{}]{}".format(rank, counts[key], key, method, flag))
        if not method.startswith(("exact", "override")):
            print("        via {!r}".format(title[:78]))

    if removed:
        print("\nno longer in the top {}: {}".format(args.top, ", ".join(sorted(removed))))

    if conflicts:
        print("\nnote field already used for something else, count not written:")
        for key, count in conflicts:
            print("  {:22s} would be {} citations".format(key, count))
        print("  merge by hand, e.g. note = {[\\href{...}{Erratum: ...}], 1234 citations}")

    matched_norms = {normalize(by_key[k]["title"]) for k in counts}
    orphans = [p for p in sorted(data["publications"], key=lambda p: -p["citations"])
               if normalize(p["title"]) not in matched_norms and not is_duplicate_record(p["title"])]
    if orphans:
        print("\nhighly cited on Scholar but not matched to a bib entry:")
        for pub in orphans[:10]:
            print("  {:6d}  {}".format(pub["citations"], pub["title"][:80]))

    not_career = [k for k in sorted(counts, key=lambda k: -counts[k])[:25] if not is_career(by_key[k])]
    if not_career and args.pool == "career":
        print("\nhighly cited but not tagged 'career' (so not printed in the CV):")
        for key in not_career[:10]:
            print("  {:6d}  {}".format(counts[key], key))

    # ---- 6. write ----------------------------------------------------------
    if args.dry_run:
        print("\n[dry run] {} line edits pending".format(
            len(edits["replace"]) + len(edits["delete"]) + sum(len(v) for v in edits["insert"].values())))
        return

    for path, lines in files.items():
        apply_edits(path, lines, edits)

    with open(CV_TEX, encoding="utf-8") as tex_file:
        tex = tex_file.read()
    updated, n_subs = HINDEX_RE.subn(lambda m: m.group(1) + str(data["hindex"]), tex)
    if n_subs and updated != tex:
        with open(CV_TEX, "w", encoding="utf-8") as tex_file:
            tex_file.write(updated)
        print("\nupdated h-index to {} in {}".format(data["hindex"], CV_TEX))

    print("wrote {} bib files".format(len(files)))


if __name__ == "__main__":
    main()
