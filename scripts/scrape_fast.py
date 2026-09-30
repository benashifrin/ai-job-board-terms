"""
Concurrent version of scrape_jobs.py for scanning thousands of boards.

Reuses the fetchers + keyword logic from scrape_jobs.py, runs them across a
thread pool, and appends matches to the CSV as they are found (so a crash or
Ctrl-C keeps everything scanned so far).

Usage:
    python scrape_fast.py sources.txt [matches.csv] [workers]
"""

import sys, csv, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import scrape_jobs as sj  # parse_source, FETCHERS, hits, get


def scan_board(ats, slug, attempt=1):
    """Return list of matched rows for one board, or [] on failure."""
    rows = []
    try:
        for job in sj.FETCHERS[ats](slug):
            if not sj.is_usa(job["location"]):
                continue
            found = sj.hits(job["blob"])
            if found:
                rows.append([slug, ats, job["title"], job["location"],
                             job["department"], job["posted"],
                             ",".join(found), job["url"]])
    except Exception as e:
        msg = str(e)
        if attempt == 1 and ("429" in msg or "timed out" in msg or "reset" in msg):
            time.sleep(2)
            return scan_board(ats, slug, attempt + 1)
        return ("err", f"{ats}:{slug} ({e})")
    return rows


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python scrape_fast.py sources.txt [matches.csv] [workers]")
    out_file = sys.argv[2] if len(sys.argv) > 2 else "matches.csv"
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    seen, sources = set(), []
    with open(sys.argv[1]) as f:
        for line in f:
            s = sj.parse_source(line)
            if s and s not in seen:
                seen.add(s)
                sources.append(s)

    total = len(sources)
    lock = threading.Lock()
    out = open(out_file, "w", newline="", encoding="utf-8")
    w = csv.writer(out)
    w.writerow(["company", "ats", "title", "location", "department",
                "posted", "keywords", "url"])
    out.flush()

    done = matched_rows = errors = 0
    companies = set()
    start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(scan_board, ats, slug): (ats, slug)
                for ats, slug in sources}
        for fut in as_completed(futs):
            res = fut.result()
            done += 1
            if isinstance(res, tuple) and res and res[0] == "err":
                errors += 1
            elif res:
                with lock:
                    for row in res:
                        w.writerow(row)
                        companies.add((row[1], row[0]))
                    out.flush()
                    matched_rows += len(res)
            if done % 200 == 0 or done == total:
                rate = done / max(time.time() - start, 1)
                eta = (total - done) / max(rate, 0.01) / 60
                sys.stderr.write(
                    f"{done}/{total} boards | {len(companies)} companies, "
                    f"{matched_rows} roles | {errors} skipped | "
                    f"{rate:.0f}/s | ETA {eta:.0f}m\n")
                sys.stderr.flush()

    out.close()
    sys.stderr.write(
        f"\nDONE: {matched_rows} roles at {len(companies)} companies "
        f"({errors} boards unreachable) -> {out_file}\n")


if __name__ == "__main__":
    main()
