"""Recompute the agreement statistics from the rater files (Guo, §6.1: the kappa procedure was unstated).

Unit of analysis: one prediction (25 cases x 3 readers = 75 items). Labels: binary correct/incorrect.
Cohen's kappa (unweighted, two categories) for each rater pair; Fleiss' kappa for the three raters together.
No prevalence adjustment. Dino's labels come from ../hand_judgments.csv via blind_key.csv; the blind raters' from rater_*.csv.
Usage: python3 agreement.py   (run from this directory; rewrites agreement.csv and prints the statistics)
"""
import csv

key = {r["item"]: (r["test_id"], r["reader"]) for r in csv.DictReader(open("blind_key.csv"))}
hj = {r["test_id"]: r for r in csv.DictReader(open("../hand_judgments.csv"))}
claude = {r["item"]: int(r["correct"]) for r in csv.DictReader(open("rater_claude.csv"))}
notes = {r["item"]: r["note"] for r in csv.DictReader(open("rater_claude.csv"))}
luna = {r["item"]: int(r["correct"]) for r in csv.DictReader(open("rater_gpt56luna.csv"))}

rows = []
for item, (t, rd) in sorted(key.items()):
    d, c, l = int(hj[t][rd + "_hand"]), claude[item], luna[item]
    rows.append(dict(item=item, test_id=t, reader=rd, score_exact=hj[t][rd + "_exact"], dino_hand=d,
                     claude_blind=c, gpt56luna_blind=l, majority=int(d + c + l >= 2), unanimous=int(d == c == l), note=notes[item]))

def cohen(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n; pe = pa * pb + (1 - pa) * (1 - pb)
    return po, 1.0 if pe == 1 else (po - pe) / (1 - pe)

def fleiss(cols):
    n, k = len(cols[0]), len(cols)
    p1 = sum(map(sum, cols)) / (n * k)
    P = [((s := sum(c[i] for c in cols)) ** 2 + (k - s) ** 2 - k) / (k * (k - 1)) for i in range(n)]
    Pe = p1 ** 2 + (1 - p1) ** 2
    return (sum(P) / n - Pe) / (1 - Pe)

D = [r["dino_hand"] for r in rows]; C = [r["claude_blind"] for r in rows]; L = [r["gpt56luna_blind"] for r in rows]
for name, (a, b) in {"dino_vs_claude": (D, C), "dino_vs_luna": (D, L), "claude_vs_luna": (C, L)}.items():
    po, k = cohen(a, b); print(f"{name}: agreement {po:.3f}  cohen_kappa {k:.3f}")
print(f"fleiss_kappa (3 raters): {fleiss([D, C, L]):.3f}")
print(f"unanimous items: {sum(r['unanimous'] for r in rows)}/{len(rows)}")
w = csv.DictWriter(open("agreement.csv", "w"), fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
