# AI terms in US job postings

How often US job postings mention specific AI tools and terms. The data comes from public Greenhouse, Lever, Ashby and Workable job boards, about 15.9k boards per scan.

## September 2026 vs July 2026

September column: 9,870 postings dated 2026-09 from 2,092 companies, out of a scan on 2026-09-30.
July column: all 17,404 matching postings from the scan on 2026-07-09.

| Term | Sept postings | Sept share | July share | Change |
|---|---:|---:|---:|---:|
| llm | 3,787 | 38.4% | 41.8% | −3.4pt |
| claude | 3,230 | 32.7% | 29.1% | +3.7pt |
| generative ai | 2,402 | 24.3% | 21.8% | +2.5pt |
| cursor | 1,275 | 12.9% | 14.4% | −1.5pt |
| openai | 1,037 | 10.5% | 14.1% | −3.6pt |
| chatgpt | 991 | 10.0% | 11.3% | −1.2pt |
| copilot | 880 | 8.9% | 8.5% | +0.4pt |
| anthropic | 724 | 7.3% | 7.6% | −0.3pt |
| prompt engineering | 644 | 6.5% | 8.1% | −1.6pt |
| gemini | 554 | 5.6% | 6.1% | −0.4pt |
| langchain | 328 | 3.3% | 4.3% | −1.0pt |
| gpt-4 | 142 | 1.4% | 1.5% | −0.1pt |
| hugging face | 140 | 1.4% | 2.0% | −0.6pt |
| midjourney | 41 | 0.4% | 0.8% | −0.4pt |
| stable diffusion | 9 | 0.1% | 0.2% | −0.1pt |

Share is the percentage of matching postings that mention the term. A single posting can mention several terms. The same table is in [`term_counts_2026-09.csv`](term_counts_2026-09.csv).

## Method

- Every board listed in `data/sources_all.txt` is fetched through its public ATS API.
- Only US postings are kept. The location filter is heuristic: states, US cities, "USA", or "remote" with no non-US signal.
- A posting counts as a match if its full JSON contains at least one of the terms below. Each term is matched as a whole word, case-insensitive; exact patterns are in `scripts/scrape_jobs.py`.
  - claude, anthropic, chatgpt, openai, gpt-4, copilot, gemini
  - llm, generative ai, prompt engineering
  - langchain, midjourney, cursor, hugging face, stable diffusion

## Caveats

- **Greenhouse dates are last-updated dates**, not first-posted dates. A "September" posting may be an older posting that was edited in September.
- **Keyword matching is literal.** For example, "cursor" can match a non-AI use of the word, and "gemini" can match non-Google uses.
- **Some boards couldn't be reached:** 5,849 in the July scan and 6,304 in September.

## Data

| File | Contents |
|---|---|
| `data/matches_2026-07.csv` | Every matching US posting from the 2026-07-09 scan |
| `data/matches_2026-09.csv` | Every matching US posting from the 2026-09-30 scan |
| `data/sources_all.txt` | The board list that was scanned |

Columns in both scan files: `company, ats, title, location, department, posted, keywords, url`.

## Reproduce

Stdlib Python only:

```sh
cd scripts
python3 scrape_fast.py ../data/sources_all.txt ../data/matches_YYYY-MM.csv 16
python3 term_counts.py ../data/matches_YYYY-MM.csv --month YYYY-MM --vs ../data/matches_2026-07.csv
```
