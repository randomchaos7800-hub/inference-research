#!/usr/bin/env python3
import json, sys, time, urllib.request
ENDPOINT=sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:8090/v1/chat/completions"
LABEL=sys.argv[2] if len(sys.argv)>2 else "model"
SYS=open("system.txt").read().strip()
TOOLS=json.load(open("tools.json"))
TASKS=[json.loads(l) for l in open("tasks.jsonl") if l.strip()]
out=[]
for t in TASKS:
    msgs=[{"role":"system","content":SYS}]+[{k:v for k,v in m.items() if v is not None} for m in t["msgs"]]
    body={"model":LABEL,"messages":msgs,"tools":TOOLS,"tool_choice":"auto","temperature":0.2,"max_tokens":512,"stream":False}
    t0=time.time()
    try:
        req=urllib.request.Request(ENDPOINT,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
        r=json.load(urllib.request.urlopen(req,timeout=300))
        dt=time.time()-t0
        m=r["choices"][0]["message"]
        tc=[{"name":c["function"]["name"],"args":c["function"]["arguments"]} for c in (m.get("tool_calls") or [])]
        usage=r.get("usage",{})
        rec={"id":t["id"],"dim":t["dim"],"expect":t["expect"],"content":(m.get("content") or "").strip()[:800],"tool_calls":tc,"latency_s":round(dt,1),"completion_tokens":usage.get("completion_tokens")}
    except Exception as e:
        rec={"id":t["id"],"dim":t["dim"],"expect":t["expect"],"error":str(e)[:200]}
    out.append(rec); print(f"  {t['id']:16s} tools={len(rec.get('tool_calls',[]))} {rec.get('latency_s','ERR')}s")
json.dump(out,open(f"results-{LABEL}.json","w"),indent=1)
print(f"→ results-{LABEL}.json")
