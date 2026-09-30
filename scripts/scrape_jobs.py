"""
Pull every public job from Greenhouse / Lever / Ashby / Workable boards
and keep the ones whose posting mentions an AI tool -- a signal that the
company already uses (or wants people who use) Claude, ChatGPT, Copilot, etc.

Usage:
    python scrape_jobs.py sources.txt [matches.csv]

sources.txt is one entry per line. Each line can be:
    - a URL copied straight from your Google results, e.g.
        https://boards.greenhouse.io/anthropic/jobs/12345
        https://jobs.lever.co/someco/uuid
        https://jobs.ashbyhq.com/someco/uuid
    - or the short form  ats:slug  e.g.  greenhouse:anthropic

Only the company slug matters, so duplicate URLs from the same board collapse.
Stdlib only, no pip installs.
"""

import sys, csv, json, time, re, datetime, urllib.request

# AI-tool mentions. Each entry is a whole-word regex so "ai" never matches
# inside "email"/"training", and "gpt" won't fire on random ids. Order-agnostic.
KEYWORD_PATTERNS = {
    "claude": r"\bclaude\b",
    "anthropic": r"\banthropic\b",
    "chatgpt": r"\bchat\s?gpt\b",
    "openai": r"\bopen\s?ai\b",
    "gpt-4": r"\bgpt[-\s]?4\w*\b",
    "copilot": r"\bcopilot\b",
    "gemini": r"\bgemini\b",
    "llm": r"\bllms?\b",
    "generative ai": r"\bgen(?:erative)?[-\s]?ai\b",
    "prompt engineering": r"\bprompt[-\s]?engineer\w*\b",
    "langchain": r"\blang\s?chain\b",
    "midjourney": r"\bmidjourney\b",
    "cursor": r"\bcursor\b",
    "hugging face": r"\bhugging\s?face\b",
    "stable diffusion": r"\bstable\s?diffusion\b",
}
COMPILED = {k: re.compile(p, re.I) for k, p in KEYWORD_PATTERNS.items()}

HEADERS = {"User-Agent": "Mozilla/5.0 (job-research)"}
DELAY = 0.5  # seconds between boards, keeps you off rate limits

# --- US-only location filter ---------------------------------------------
US_STATES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
]
US_ABBR = (r"\b(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|"
           r"MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|"
           r"TX|UT|VT|VA|WA|WV|WI|WY|DC)\b")
US_CITIES = ["san francisco", "new york", "los angeles", "seattle", "boston",
             "austin", "chicago", "denver", "atlanta", "washington", "dc",
             "san jose", "palo alto", "mountain view", "cupertino", "menlo park",
             "san diego", "portland", "miami", "dallas", "houston", "philadelphia",
             "brooklyn", "sunnyvale", "santa clara", "san mateo", "redwood city"]
US_COUNTRY = re.compile(r"\b(united states|u\.?s\.?a?\.?|usa)\b", re.I)
US_ABBR_RX = re.compile(US_ABBR)
# non-US signals that override a bare "remote"
NON_US = re.compile(
    r"\b(united kingdom|england|london|manchester|ireland|dublin|canada|toronto|"
    r"vancouver|germany|berlin|munich|france|paris|spain|madrid|barcelona|"
    r"netherlands|amsterdam|india|bangalore|bengaluru|singapore|australia|sydney|"
    r"melbourne|brazil|mexico|poland|warsaw|portugal|lisbon|emea|apac|latam|"
    r"europe|uk|eu)\b", re.I)


def is_usa(location):
    loc = (location or "").strip().lower()
    if not loc:
        return False
    if US_COUNTRY.search(loc):
        return True
    if any(st in loc for st in US_STATES):
        return True
    if US_ABBR_RX.search(location or ""):
        return True
    if any(c in loc for c in US_CITIES):
        return True
    # accept plain "remote" only when nothing points abroad
    if "remote" in loc and not NON_US.search(loc):
        return True
    return False


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def ms_to_date(ms):
    if not ms:
        return ""
    return datetime.datetime.utcfromtimestamp(ms / 1000).date().isoformat()


def parse_source(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = re.search(r"greenhouse\.io/(?:v1/boards/|embed/job_board\?for=)?([^/?#]+)", line)
    if m:
        return ("greenhouse", m.group(1))
    m = re.search(r"lever\.co/(?:v0/postings/)?([^/?#]+)", line)
    if m:
        return ("lever", m.group(1))
    m = re.search(r"ashbyhq\.com/(?:posting-api/job-board/)?([^/?#]+)", line)
    if m:
        return ("ashby", m.group(1))
    m = re.search(r"apply\.workable\.com/([^/?#]+)", line)
    if m and m.group(1) not in ("j", "jobs"):
        return ("workable", m.group(1))
    m = re.search(r"([^/?#.]+)\.workable\.com", line)
    if m and m.group(1) not in ("www", "apply"):
        return ("workable", m.group(1))
    if ":" in line:
        ats, slug = line.split(":", 1)
        if ats in ("greenhouse", "lever", "ashby", "workable"):
            return (ats, slug.strip())
    return None


def fetch_greenhouse(slug):
    data = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    for j in data.get("jobs", []):
        yield {
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "department": "; ".join(d.get("name", "") for d in j.get("departments", [])),
            "posted": j.get("updated_at", ""),
            "url": j.get("absolute_url", ""),
            "blob": json.dumps(j),
        }


def fetch_lever(slug):
    for j in get(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        cats = j.get("categories", {}) or {}
        yield {
            "title": j.get("text", ""),
            "location": cats.get("location", ""),
            "department": cats.get("team", ""),
            "posted": ms_to_date(j.get("createdAt")),
            "url": j.get("hostedUrl", ""),
            "blob": json.dumps(j),
        }


def fetch_ashby(slug):
    data = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    for j in data.get("jobs", []):
        yield {
            "title": j.get("title", ""),
            "location": j.get("location", ""),
            "department": j.get("department", ""),
            "posted": j.get("publishedAt", ""),
            "url": j.get("jobUrl", ""),
            "blob": json.dumps(j),
        }


def fetch_workable(slug):
    data = get(f"https://www.workable.com/api/accounts/{slug}?details=true")
    for j in data.get("jobs", []):
        yield {
            "title": j.get("title", ""),
            "location": j.get("location") or j.get("city", ""),
            "department": j.get("department", ""),
            "posted": j.get("published_on", "") or j.get("created_at", ""),
            "url": j.get("url") or j.get("shortlink", ""),
            "blob": json.dumps(j),
        }


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "workable": fetch_workable,
}


def hits(blob):
    return [k for k, rx in COMPILED.items() if rx.search(blob)]


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python scrape_jobs.py sources.txt [matches.csv]")
    out_file = sys.argv[2] if len(sys.argv) > 2 else "matches.csv"

    seen, sources = set(), []
    with open(sys.argv[1]) as f:
        for line in f:
            s = parse_source(line)
            if s and s not in seen:
                seen.add(s)
                sources.append(s)

    rows = []
    companies = set()
    for i, (ats, slug) in enumerate(sources, 1):
        try:
            for job in FETCHERS[ats](slug):
                found = hits(job["blob"])
                if found:
                    companies.add(slug)
                    rows.append([slug, ats, job["title"], job["location"],
                                 job["department"], job["posted"],
                                 ",".join(found), job["url"]])
        except Exception as e:
            sys.stderr.write(f"skip {ats}:{slug} ({e})\n")
        if i % 25 == 0:
            sys.stderr.write(f"  ...{i}/{len(sources)} boards, {len(companies)} hits so far\n")
        time.sleep(DELAY)

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company", "ats", "title", "location", "department",
                    "posted", "keywords", "url"])
        w.writerows(rows)

    sys.stderr.write(
        f"{len(rows)} matching roles at {len(companies)} companies "
        f"across {len(sources)} boards -> {out_file}\n"
    )


if __name__ == "__main__":
    main()
