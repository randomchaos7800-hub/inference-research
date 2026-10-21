#!/usr/bin/env python3
"""Replay offline-ops scenarios against an OpenAI-compatible llama-server.

    harness.py --base http://127.0.0.1:8091 --label qwen-iq4 --out results/q.jsonl [--seed 1] [--only diag,iphone]

The model gets offline Hermes' SOUL and one `terminal` tool. Commands are answered from the
scenario fixtures (scenarios.py); deny-listed commands are blocked the way Hermes blocks them.
One JSON line per scenario: full transcript + mechanical counters. Judging is separate.
"""
import argparse, fnmatch, json, re, time, urllib.request
import scenarios as S

DENY = ['*nmcli c* up*', '*nmcli c* down*', '*nmcli d* disconnect*', '*nmcli networking off*',
        '*nmcli radio*off*', '*tailscale down*', '*travel off*',
        '*systemctl restart NetworkManager*', '*systemctl stop NetworkManager*']

TOOLS = [{"type": "function", "function": {
    "name": "terminal",
    "description": "Run a shell command on cha0tikp14 as user dino and return its output and exit code.",
    "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "The shell command to run"}},
                   "required": ["command"]}}}]


def answer(cmd, fixtures, state=None):
    """Split compound commands, answer each piece from scenario fixtures then BASE."""
    if any(fnmatch.fnmatch(cmd, d) for d in DENY):
        return {"output": "", "exit_code": 126, "error": "BLOCKED by approvals.deny: this command is denied for the agent. Print it for Dino to run himself."}, True
    pieces = [p.strip() for p in re.split(r"\s*(?:;|&&|\|\||\n)\s*", cmd) if p.strip()]
    outs, code = [], 0
    for p in pieces:
        head = p.split("|")[0].strip()
        if head.startswith("echo "):
            outs.append(head[5:].strip("'\"")); continue
        hit = None
        for rx, out, ec in fixtures + S.BASE:
            mm = re.search(rx, head) or re.search(rx, p)
            if mm:
                if "{1}" in out and mm.groups():
                    out = out.replace("{1}", mm.group(1))
                hit = (out, ec); break
        if hit is None:
            hit = ("(no output recorded for this command in the replay environment)", 127)
        outs.append(hit[0]); code = hit[1]
    return {"output": "\n".join(o for o in outs if o is not None), "exit_code": code, "error": None}, False


def chat(base, messages, seed, timeout=1200):
    body = {"model": "local", "messages": messages, "tools": TOOLS, "temperature": 0.6, "top_p": 0.95,
            "max_tokens": 8192, "seed": seed}
    req = urllib.request.Request(base + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def run(base, name, sc, seed, soul, max_steps=24):
    msgs = [{"role": "system", "content": soul}]
    log = dict(scenario=name, seed=seed, tool_calls=0, denied=0, malformed=0, leaked_text_calls=0,
               steps=0, prompt_tokens=0, completion_tokens=0, errors=[], finals=[], fixed_at_call=None)
    state = {"fixed": False}
    t0 = time.time()
    for turn in sc["turns"]:
        msgs.append({"role": "user", "content": turn})
        for _ in range(max_steps):
            log["steps"] += 1
            try:
                r = chat(base, msgs, seed)
            except Exception as e:
                log["errors"].append(f"request: {e}"); break
            u = r.get("usage", {})
            log["prompt_tokens"] = max(log["prompt_tokens"], u.get("prompt_tokens", 0))
            log["completion_tokens"] += u.get("completion_tokens", 0)
            m = r["choices"][0]["message"]
            fr = r["choices"][0].get("finish_reason")
            calls = m.get("tool_calls") or []
            content = m.get("content") or ""
            entry = {"role": "assistant", "content": content}
            if m.get("reasoning_content"):
                entry["reasoning_content"] = m["reasoning_content"]
            if calls:
                entry["tool_calls"] = calls
            msgs.append(entry)
            if not calls:
                if re.search(r"<tool_call>|\"name\"\s*:\s*\"terminal\"|<function=", content):
                    log["leaked_text_calls"] += 1
                if fr == "length":
                    log["errors"].append("finish_reason=length")
                log["finals"].append(content)
                break
            for c in calls:
                log["tool_calls"] += 1
                try:
                    cmd = json.loads(c["function"]["arguments"]).get("command", "")
                except Exception:
                    log["malformed"] += 1
                    msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": json.dumps(
                        {"output": "", "exit_code": 2, "error": "malformed tool arguments"})}); continue
                fx = (sc.get("after", []) + sc["fixtures"]) if state["fixed"] else sc["fixtures"]
                res, blocked = answer(cmd, fx)
                log["denied"] += blocked
                if not blocked and not state["fixed"] and any(re.search(r, cmd) for r in sc.get("fixed_by", [])):
                    state["fixed"] = True; log["fixed_at_call"] = log["tool_calls"]
                msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": json.dumps(res)})
        else:
            log["errors"].append("max_steps")
    log["wall_s"] = round(time.time() - t0, 1)
    log["transcript"] = msgs[1:]
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8091")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    soul = open(__file__.rsplit("/", 1)[0] + "/soul.md").read()
    names = [n for n in S.SCEN if not a.only or n in a.only.split(",")]
    for n in names:
        res = run(a.base, n, S.SCEN[n], a.seed, soul)
        res["label"] = a.label
        with open(a.out, "a") as f:
            f.write(json.dumps(res) + "\n")
        print(f"{a.label} {n} seed={a.seed} calls={res['tool_calls']} denied={res['denied']} "
              f"leaked={res['leaked_text_calls']} err={res['errors']} {res['wall_s']}s", flush=True)
    print("HARNESS-DONE", flush=True)
