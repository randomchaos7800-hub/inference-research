#!/usr/bin/env python3
"""X morning post — scan trends, write tweet in @cha0tikdino voice, post. Runs 6AM daily."""

import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import slack
import inference

VAULT = os.path.expanduser("~/.vault/vault.sh")
X_AGENT = os.path.expanduser("~/.kato/scripts/x-agent.ts")


def vault_get(key):
    r = subprocess.run([VAULT, "get", key], capture_output=True, text=True)
    return r.stdout.strip()


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "PATH": "/home/dino/.nvm/versions/node/v22.22.0/bin:/home/dino/.local/bin:" + os.environ.get("PATH", "")})
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "(timed out)"


def tweet_format():
    formats = [
        "OBSERVATION: personal experience opener — I/After/Running, draws on your own ops",
        "DATA POINT: lead with a specific number or benchmark — t/s, uptime, cost delta",
        "CONTRARIAN: name the common take first, then flip it — grounded not edgy",
        "QUESTION: a genuine open question to the local AI community",
        "BEHIND THE SCENES: something people don't expect about running local AI ops",
        "PRACTICAL TIP: starts with a specific situation, ends with what actually works",
        "HOT TAKE: one declarative sentence that makes cloud-first people think",
    ]
    return formats[date.today().toordinal() % len(formats)]


def main():
    today = date.today().isoformat()
    xai_key = vault_get("xai_api_key")

    if not xai_key:
        slack.post(f"⚠️ x-post-morning: xai_api_key not in vault — skipped")
        return

    # Get trending local AI topics via xai
    trend_cmd = (
        f'XAI_API_KEY={xai_key} npx tsx {X_AGENT} '
        f'"what are the top 5 active conversations in local AI, self-hosted LLM, consumer GPU, '
        f'and AI agents in the last 24 hours? List topics and brief description."'
    )
    trends = run(trend_cmd, timeout=60)

    fmt = tweet_format()

    system = (
        "@cha0tikdino is Dino Vitale: 55, systems architect, runs local AI 24/7 on consumer hardware. "
        "Direct, specific, no hype, no hashtags. First person. Technical but readable."
    )
    prompt = (
        f"Today is {today}. Write ONE tweet for @cha0tikdino.\n\n"
        f"Format to use: {fmt}\n\n"
        f"Trending topics today:\n{trends}\n\n"
        f"Under 260 chars. No hashtags. Use a specific number if you have one. "
        f"Pick the angle from the trending topics that fits the format best."
    )

    tweet = inference.ask(prompt, system=system, max_tokens=100, temperature=0.8, timeout=60)
    tweet = tweet.strip('"').strip()

    # Post to X
    post_result = run(f'/home/dino/.local/bin/x-cli tweet post "{tweet}"', timeout=30)

    # Report to Slack
    msg = (
        f"*🐦 X Morning Post — {today}*\n"
        f"Format: _{fmt}_\n\n"
        f"*Posted:* {tweet}\n\n"
        f"Result: {post_result[:200]}"
    )
    slack.post(msg)
    print(f"X morning post done — {today}")


if __name__ == "__main__":
    main()
