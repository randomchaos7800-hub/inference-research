# How "215+ benchmark runs" is counted

The public claim is **215+ raw benchmark runs as of 2026-06-27** — a floor, frozen at the
date it was first published. The current countable total from the table below is
**491 runs (as of 2026-07-09**, after the April–May campaign archive was consolidated
onto this branch**)**. Here is what the count includes and how to audit it from this repo alone:

| Source | What a "run" is | Rows/entries |
|---|---|---|
| [tower/campaigns-2026-04-05/](tower/campaigns-2026-04-05/) TSVs | One autoresearch iteration = one served-model config benchmarked | 268 data rows |
| [tower/frank/](tower/frank/) TSVs | Same (Frank workflow sweeps) | 113 rows |
| [tower/ornith/](tower/ornith/) suite JSONs | One timed generation run per entry | 41 |
| [tower/lucebox/](tower/lucebox/) JSONs | One controlled run per entry | 67 |
| [tower/genesis/warm-20260708.json](tower/genesis/warm-20260708.json) | Live warm verification runs | 2 |

Notes on honest counting:

- **Eval cases are not counted as benchmark runs.** The LangChain suites (3 × 66 cases)
  and HumanEval (164 completions) measure capability, not serving performance — they are
  receipts for the quality claims, not part of the 215+ throughput-experiment count.
- Some campaign TSVs overlap conceptually (re-runs after code fixes are kept — e.g. the
  frank pre/post loop-rebuild files); the 2026-06-27 count of 215+ predates several of the
  archived TSVs being consolidated here, which is why the countable total (268+ TSV rows
  alone) now exceeds the public claim. The public number is a floor, not a ceiling.
- **Milestone experiments:** the "30+ milestone experiments" phrasing on the website counts
  the entries on the [localfamo.us](https://localfamo.us) interactive timeline (31 as of
  2026-06-27). Program-level verdict documents in this repo number 9, indexed in
  [RESULTS.md](RESULTS.md) — the timeline is finer-grained than the program index.
