# Adjudication of the three judging disagreements

Run 2026-09-27, closing the step Guo's protocol specifies and the 2026-09-26 judging
skipped. It is a **separate evidence layer**: no original rater label, no `hand` column and
no reported score is overwritten by anything here.

## Method

- **Adjudicator:** `qwen/qwen3.8-max-prime` via OpenRouter — a family used by **no original
  rater** (Dino Vitale, Claude/Fable 5.1, gpt-5.6-luna, Grok) and by **no reader under
  test** (gpt-5.6-terra, Sonnet 5, Opus 5).
- **Inputs:** the fixed written criterion verbatim, the question, the expected fact, the
  candidate answer, and the four locked independent labels. Labels were shown **anonymised**
  (R1–R4) and the adjudicator was told not to defer to the majority, so it could not
  recognise or defer to the human rater.
- **Locked first:** the rater files were committed before this ran.
- **Robustness check:** re-run with `deepseek/deepseek-v4.1-flash`, a second uninvolved
  family. Both agree on all three items — `robustness_check_deepseek.{csv,json}`.
- Files: `adjudication.csv`, `adjudication.json` (adjudicated label + rationale per item).

**This is model adjudication, not human adjudication.** Guo's limitation about model-based
judging applies to this layer too. Whether it satisfies his "uninvolved third party" is his
call, not ours.

## Outcome

| Item | Case | Run | R1–R4 | Majority | Adjudicated |
|---|---|---|---|---|---|
| K003 | lme_0012 | sonnet_archive | 1,0,0,0 | incorrect | **incorrect** — agrees with majority |
| K056 | lme_0002 | opus_archive | 0,1,1,1 | correct | **correct** — agrees with majority |
| K120 | lme_0008 | sonnet_archive_repeat | 1,1,1,0 | correct | **incorrect** — *overturns* the majority |

## Two corrections this forced

**1. "All three disagreements fall in one class" was wrong.** That claim appeared in this
run's README, in the paper, and was carried into Guo's v2 RC2 §6.2 on our word. Only
`lme_0002` and `lme_0008` are "states the expected fact while disclaiming confidence".
`lme_0012` is not: the answer is *"I don't have access to your Spotify account, so I can't
check"* and never states 20. Under the written rule an "I don't have that" is a miss
regardless. The three model raters had it right; the human rater's label is the outlier and
does not survive the criterion.

**2. `lme_0008` does not support a stable binary judgment either.** The adjudicators judged
each item alone. Placed side by side, `K048` (sonnet_archive, unanimously **correct**) and
`K120` (sonnet_archive_repeat, adjudicated **incorrect**) are substantively the same answer
from the same reader on the same case: both name the "Love is in the Air" dinner on
Valentine's Day, both state it was not described as an animal shelter event. `K120` states
the date *more* explicitly ("February 14") and disclaims *harder*, and that is the one that
loses. The rule cannot separate them stably, which is the same defect already documented for
`lme_0002` — so `lme_0008` is a **candidate unscorable item**, flagged here, not adopted.

## What is deliberately NOT changed

Adopting the `K120` adjudication would move **sonnet repeat from 9/25 (36%) to 8/25 (32%)**.
We have not made that change. Under Guo's protocol adjudicated labels sit beside the
originals rather than replacing them, and given correction 2 the better-supported reading is
that the item is unscorable rather than a miss. Both calls are Guo's as co-author.
