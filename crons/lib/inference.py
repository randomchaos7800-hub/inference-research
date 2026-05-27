"""Local inference via proxy at :8010 — OpenAI-compatible."""

import json
import urllib.request

PROXY = "http://100.120.50.35:8010/v1/chat/completions"


def ask(prompt, system=None, max_tokens=1024, temperature=0.7, timeout=180):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = json.dumps({
        "model": "auto",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(
        PROXY,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
        return resp["choices"][0]["message"]["content"].strip()
