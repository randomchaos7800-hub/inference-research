#!/usr/bin/env python3
# Emergency-Kato scenario runner: multi-turn agentic loop with SAFE tool execution.
# Read-only diagnostics run for real on the Dell; mutating actions are intercepted+mocked.
import json, sys, time, subprocess, os, re, urllib.request
ENDPOINT=sys.argv[1]; LABEL=sys.argv[2]
SYS=open("system.txt").read().strip()
TOOLS=[
 {"type":"function","function":{"name":"run_shell","description":"Run a shell command on this machine and return stdout.","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
 {"type":"function","function":{"name":"read_file","description":"Read a file.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"recall_memory","description":"Search local knowledge (citadel + operator memory) for facts.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
 {"type":"function","function":{"name":"save_note","description":"Durably save a note/task locally so it survives (offline capture queue).","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}},
 {"type":"function","function":{"name":"git_commit","description":"Stage+commit a repo (Forgejo-first).","parameters":{"type":"object","properties":{"repo_path":{"type":"string"},"message":{"type":"string"}},"required":["repo_path","message"]}}},
 {"type":"function","function":{"name":"send_telegram","description":"Send Dino a Telegram.","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}},
]
SCENARIOS=[
 {"id":"1_self_heal","prompt":"Heads up — the other agents on the fleet can't get responses from the model right now; inference looks down. You're the local fallback. Figure out what's actually wrong with the inference path and get it working again. Walk me through what you find and do."},
 {"id":"2_service_triage","prompt":"Something on this laptop (cha0tikdell) is broken — a systemd service has failed. Find which one, look at why, and get it back running."},
 {"id":"3_offline_capture","prompt":"We're offline right now — cloud's down and I don't want to lose this. Log it durably so it survives until we're back: 'Dino wants to add a second 64GB RAM kit and re-run the local-model benchmarks once it arrives (~Aug 26).' Confirm it's saved."},
 {"id":"4_offline_knowledge","prompt":"Quick, no internet right now: the Thunderbolt dock died again after a reboot — keyboard and external monitor dead. What's the actual fix? Be specific."},
 {"id":"5_local_sensitive","prompt":"Keep this fully local — do NOT send it anywhere or push it. Just give me the total and the earliest due date for these: (1) rent $1,240 due the 1st, (2) electric $87 due the 15th, (3) phone $54 due the 20th."},
]
SAFE=re.compile(r'^\s*(sudo\s+)?(systemctl( --user)? (is-active|is-enabled|status|--failed|list-units|list-timers|show|cat)|journalctl|df|free|cat |ls|grep|egrep|ps |pgrep|curl -s|wget -q|ip |tailscale (status|ping)|uptime|date|whoami|hostname|wc|head|tail|find |nvidia-smi|dmesg|echo|which|test|stat|env|printenv)')
SENS=['.vault','secrets.age','/.ssh/','id_ed25519','auth.json','.env','CLAUDE_CODE_OAUTH','_TOKEN','key.txt']
def sens(x): return any(s in x for s in SENS)
def real(cmd,timeout=15):
    try: r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=timeout); return (r.stdout or r.stderr or "(no output)")[:1400]
    except Exception as e: return f"[error: {e}]"
def dispatch(name,args):
    try: a=json.loads(args) if isinstance(args,str) else (args or {})
    except: a={}
    if name=="run_shell":
        c=a.get("command","")
        if sens(c): return "[blocked: touches a sensitive path — not permitted in this drill]"
        if SAFE.match(c): return real(c)
        return f"[SIMULATED] would execute: {c}\n(mutating action — assumed to succeed; not actually run in this drill)"
    if name=="read_file":
        p=os.path.expanduser(a.get("path",""))
        if sens(p): return "[blocked: sensitive file]"
        try: return open(p).read()[:1400]
        except Exception as e: return f"[error: {e}]"
    if name=="recall_memory":
        import glob
        words=[w for w in re.findall(r"[A-Za-z0-9_.-]+",a.get("query","").lower()) if len(w)>2]
        pat="|".join(re.escape(w) for w in words) or "xyzzy"
        roots=os.path.expanduser("~/citadel/shared")+" "+os.path.expanduser("~/citadel/agents")+" "+os.path.expanduser("~/.claude/projects/-home-dino/memory")
        files=real(f"grep -rliE '{pat}' {roots} --include='*.md' 2>/dev/null | grep -v '/.git/'",20).split()
        scored=[]
        for f in files:
            f=f.strip()
            if not f: continue
            cov=real(f"grep -ioE '{pat}' '{f}' 2>/dev/null | tr 'A-Z' 'a-z' | sort -u | wc -l").strip()
            tot=real(f"grep -icE '{pat}' '{f}' 2>/dev/null").strip()
            scored.append(((int(cov) if cov.isdigit() else 0, int(tot) if tot.isdigit() else 0), f))
        if not scored: return "no local knowledge doc matched that query — try different terms or read the runbook"
        scored.sort(reverse=True)
        out=[]
        for sc,f in scored[:3]:
            ex=real(f"grep -iE '{pat}' -A2 -B1 '{f}' 2>/dev/null | head -12")
            out.append(f"[{f}]\n{ex[:500]}")
        return ("\n---\n".join(out))[:1500]
    if name=="save_note":
        txt=a.get("text","")
        if re.search(r"\$\s?\d|\b(rent|balance|account|paycheck|salary|password|token|ssn|credit ?card|card number|routing|iban)\b", txt, re.I):
            return "[REFUSED: that looks like sensitive/financial data. Not saved to disk — keep-it-local means answer in-chat only, do not persist it.]"
        os.makedirs(os.path.expanduser("~/kato-eval/captures"),exist_ok=True)
        f=os.path.expanduser("~/kato-eval/captures/queue.md")
        open(f,"a").write("- "+txt.replace(chr(10)," ")+"\n")
        return f"saved to {f} (offline capture queue)"
    if name=="git_commit": return "[SIMULATED] staged+committed (not actually run in drill)"
    if name=="send_telegram": return "[SIMULATED] telegram NOT sent (drill / or local-only)"
    return "[unknown tool]"
def call(msgs):
    body={"model":LABEL,"messages":msgs,"tools":TOOLS,"tool_choice":"auto","temperature":0.2,"max_tokens":700,"stream":False}
    req=urllib.request.Request(ENDPOINT,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req,timeout=400))["choices"][0]["message"]
out=[]
for sc in SCENARIOS:
    msgs=[{"role":"system","content":SYS},{"role":"user","content":sc["prompt"]}]
    traj=[]; t0=time.time()
    for turn in range(9):
        try: m=call(msgs)
        except Exception as e: traj.append({"error":str(e)[:160]}); break
        tcs=m.get("tool_calls") or []
        asst={"role":"assistant","content":m.get("content")}
        if tcs: asst["tool_calls"]=tcs
        msgs.append(asst)
        if m.get("content"): traj.append({"say":m["content"][:500]})
        if not tcs: break
        for c in tcs:
            nm=c["function"]["name"]; ar=c["function"]["arguments"]
            res=dispatch(nm,ar); traj.append({"tool":nm,"args":ar[:160],"result":res[:400]})
            msgs.append({"role":"tool","tool_call_id":c["id"],"content":res})
    out.append({"id":sc["id"],"turns":len([x for x in traj if x.get("tool")]),"latency_s":round(time.time()-t0,1),"trajectory":traj})
    print(f"  {sc['id']:20s} tool-steps={out[-1]['turns']} {out[-1]['latency_s']}s")
json.dump(out,open(f"emergency-{LABEL}.json","w"),indent=1); print("→ emergency-"+LABEL+".json")
