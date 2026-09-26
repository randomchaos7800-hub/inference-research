# Judge reliability — blind second and third rater on the September predictions

**Run 2026-09-25.** This is Guo's T5 (Failure Attribution Test Matrix) applied to the existing
75 predictions (25 cases × 3 readers). The original hand-judgment column is untouched.

## Protocol

- **Items:** every `predicted` string from the three September JSONL files, paired with its
  question and expected answer. Shuffled with a fixed seed (`20260925`) and relabeled `J01`–`J75`.
  `blind_items.csv` is what the raters saw; `blind_key.csv` maps items back to case and reader.
- **Blinding:** raters saw no reader identity, no `score_exact`, no position data, and no
  original hand label.
- **Rule** (from the run README): correct iff the answer states the expected fact. An "I don't have
  that" is a miss regardless of what the scorer says. Empty answers are misses. A hedge
  ("probably X") still states X.
- **Raters:**
  1. Dino Vitale, the original single-pass hand judge (2026-09-21), not blind.
  2. Claude (Fable 5.1, the lab's coding agent), blind. Rated by reading `blind_items.csv`.
     `rater_claude.csv`, with notes on the hedged and empty items.
  3. gpt-5.6-luna via the lab gateway, blind, temperature 0, three batches of 25, strict
     `ITEM,0|1` output. `rater_gpt56luna.csv`.
  4. Grok (xAI, `grok -p` CLI, default model), blind, same prompt and batches, added
     2026-09-26 as a third model family. `rater_grok.csv`.
- **Adjudication rule:** majority of four; ties would go to a documented third review (none occurred). `agreement.csv` has all three labels per item plus
  the majority and a unanimity flag.

## Result

| Comparison | Agreement | Cohen's κ |
|---|---|---|
| Dino vs Claude | 75/75 | 1.00 |
| Dino vs gpt-5.6-luna | 75/75 | 1.00 |
| Dino vs Grok | 75/75 | 1.00 |
| Claude vs gpt-5.6-luna | 75/75 | 1.00 |
| Claude vs Grok | 75/75 | 1.00 |
| gpt-5.6-luna vs Grok | 75/75 | 1.00 |
| Four raters, Fleiss' κ | | 1.00 |

Per-reader totals are identical under every rater and under the majority: terra 9/25,
sonnet 10/25, opus 10/25. No item needed adjudication.

The two items the rule could have split on were the hedged Target answers (`lme_0002`, Sonnet and
Opus: "Probably at Target", "Target, most likely"). All three raters counted them as stating the
fact. The scorer false positive (`lme_0014`, "10%" inside an "I don't have that" answer) was a
unanimous miss.

## What this moves

On the Failure Attribution Rubric, judge confidence for the September run goes from J1
(single-pass, no second rater) to **J2** (corroborated, no unresolved disagreement) for all 75
items. We first wrote J3; Guo's combined report (2026-09-26, §6.2) places it at J2 because two
raters are models, one shares a family with terra, and no per-item rationale was recorded for the
model rater. He wrote the rubric, so his level stands. `rubric_annotations.csv` one level up carries
J2 per item.

**Statistic:** unit = one prediction (75). Cohen's κ, unweighted, two categories, no prevalence
adjustment, per rater pair; Fleiss' κ for the three raters. Recompute with `agreement.py`.

## Caveats, stated plainly

- Three of the four raters are language models. The independence claim is about blinding and
  separate judgment, not about human raters.
- The Claude rater had, earlier the same day, read the original CSV notes for three cases
  (`lme_0007`, `lme_0008`, `lme_0014`) while verifying Guo's audit. It rated blind to item
  identity, but that exposure is real and is disclosed here.
- gpt-5.6-luna is in the same model family as the terra reader. Grok (xAI) was added on
  2026-09-26 as a rater from a family that read none of the predictions; it agreed on all 75.
- 75 short factual items under a strict rule is an easy agreement task. κ = 1.0 here says the
  rule is unambiguous on this set, not that the rule would hold on multi-session or temporal
  question types.
