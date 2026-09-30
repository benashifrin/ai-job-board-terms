"""Rank AI terms by how many postings mention them, optionally limited to a
posting month, and compare against a baseline scan.

Usage:
    python term_counts.py matches_2026-09.csv [--month 2026-09] [--vs matches.csv]
"""
import sys, csv, collections, argparse

ap = argparse.ArgumentParser()
ap.add_argument("file")
ap.add_argument("--month", help="YYYY-MM; keep postings whose posted date starts with it")
ap.add_argument("--vs", help="baseline matches csv (whole file)")
a = ap.parse_args()


def tally(path, month=None):
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8"))
            if not month or r["posted"].startswith(month)]
    c = collections.Counter(k for r in rows for k in r["keywords"].split(",") if k)
    return len(rows), len({r["company"] for r in rows}), c


n, co, c = tally(a.file, a.month)
print(f"=== {a.file}{' month ' + a.month if a.month else ''}: {n} postings, {co} companies ===")
if a.vs:
    bn, bco, bc = tally(a.vs)
    print(f"    baseline {a.vs}: {bn} postings, {bco} companies\n")
    print(f"  {'TERM':<20}{'POSTINGS':>9}{'SHARE':>8}{'BASE SHARE':>12}{'CHANGE':>9}")
else:
    print(f"\n  {'TERM':<20}{'POSTINGS':>9}{'SHARE':>8}")
for k, v in c.most_common():
    s = v * 100 / n
    line = f"  {k:<20}{v:>9}{s:>7.1f}%"
    if a.vs:
        b = bc[k] * 100 / bn
        line += f"{b:>11.1f}%{s - b:>+8.1f}pt"
    print(line)
