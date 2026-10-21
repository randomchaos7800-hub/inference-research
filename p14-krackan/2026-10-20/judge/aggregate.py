"""Unblind: join judge scores with the key; per-model totals + mechanical counters."""
import json, glob, collections, statistics as st
key = json.load(open('judge/KEY-do-not-show-judges.json'))
mech = {}
for l in open('raw/quality.jsonl'):
    r = json.loads(l); mech[(r['label'], r['seed'], r['scenario'])] = r
by = collections.defaultdict(lambda: collections.defaultdict(list))
viol = collections.defaultdict(list)
missing = []
for f in sorted(glob.glob('judge/scores-*.json')):
    j = json.load(open(f)); sc = j['scenario']
    for code, s in j['runs'].items():
        k = key[code]; by[k['label']][sc].append(s)
        for v in s.get('violations', []): viol[k['label']].append(f"{sc} s{k['seed']}: {v}")
for code, k in key.items():
    sc = {'DIA':'diag','IPH':'iphone','PSK':'pskflags','MTP':'mtppath','UMA':'uma','TAI':'tailscale','BAT':'battery','SLO':'slowboot','THE':'thermal'}[code[:3]]
    if sc not in by[k['label']]: missing.append(code)
scen = ['diag','iphone','pskflags','mtppath','uma','tailscale','battery','slowboot','thermal']
labels = sorted(by, key=lambda L: -sum(s['total'] for v in by[L].values() for s in v))
print("mean total /11 per scenario (2 seeds)")
print(f"{'model':16}" + "".join(f"{s[:7]:>8}" for s in scen) + f"{'MEAN':>7}{'exMTP':>7}{'dx':>5}{'fix':>5}{'bnd':>5}{'acc':>5}")
for L in labels:
    row = [st.mean(s['total'] for s in by[L][sc]) if by[L][sc] else float('nan') for sc in scen]
    allr = [s for sc in scen for s in by[L][sc]]
    ex = [s['total'] for sc in scen if sc != 'mtppath' for s in by[L][sc]]
    print(f"{L:16}" + "".join(f"{x:8.1f}" for x in row) + f"{st.mean(s['total'] for s in allr):7.2f}{st.mean(ex):7.2f}"
          + "".join(f"{st.mean(s[d] for s in allr):5.2f}" for d in ['diagnosis','resolution','boundaries','accuracy']))
print("\nmechanical (18 runs each)")
for L in labels:
    rs = [v for (l, _, _), v in mech.items() if l == L]
    print(f"{L:16} calls={sum(r['tool_calls'] for r in rs):4} denied={sum(r['denied'] for r in rs)} malformed={sum(r['malformed'] for r in rs)} "
          f"leaked={sum(r['leaked_text_calls'] for r in rs)} max_steps={sum('max_steps' in r['errors'] for r in rs)} "
          f"length={sum('finish_reason=length' in r['errors'] for r in rs)} req_err={sum(any(e.startswith('request') for e in r['errors']) for r in rs)} "
          f"wall={sum(r['wall_s'] for r in rs)/60:.0f}min")
print("\nviolations")
for L in labels:
    for v in viol[L]: print(f"  {L}: {v}")
if missing: print("MISSING scores:", missing)
