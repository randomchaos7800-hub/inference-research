#!/usr/bin/env python3
"""X afternoon post — topic rotation, write tweet, post. Runs 4PM daily."""

import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import slack
import inference

VAULT = os.path.expanduser("~/.vault/vault.sh")

TOPICS = [
    "local inference economics: real cost per token vs cloud API bills",
    "data sovereignty: what never leaves your house and why that matters",
    "running AI agents 24/7 locally: what breaks and what you learn",
    "consumer GPU performance: actual t/s numbers vs marketing claims",
    "the collapsing cost barrier to local AI",
    "owning your compute end to end: what that looks like day to day",
    "model quality vs speed tradeoffs: how to make the call for real tasks",
    "the gap between a local AI demo and actual local production",
    "what your self-hosted stack actually looks like after it's working",
    "local AI advantages for solo operators that large teams can't replicate",
    "context and memory management for always-on agents: lessons learned",
    "what surprised you most after months of running local AI 24/7",
    "what cloud AI marketing doesn't mention about consumer hardware",
    "building without API dependency: what changes when you own inference",
]


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "PATH": "/home/dino/.local/bin:" + os.environ.get("PATH", "")})
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "(timed out)"


def main():
    today = date.today()
    topic = TOPICS[today.toordinal() % len(TOPICS)]

    system = (
        "@cha0tikdino is Dino Vitale: 55, systems architect, runs local AI 24/7 on consumer hardware. "
        "Direct, specific, no hype, no hashtags. First person. Under 280 chars."
    )
    prompt = (
        f"Today is {today.isoformat()}. Write ONE tweet for @cha0tikdino about:\n\n"
        f"{topic}\n\n"
        "Use real numbers or specific examples when possible. "
        "No hashtags. No corporate speak. No hype. Under 280 chars."
    )

    tweet = inference.ask(prompt, system=system, max_tokens=100, temperature=0.8, timeout=60)
    tweet = tweet.strip('"').strip()

    post_result = run(f'/home/dino/.local/bin/x-cli tweet post "{tweet}"')

    msg = (
        f"*🐦 X Afternoon Post — {today.isoformat()}*\n"
        f"Topic: _{topic}_\n\n"
        f"*Posted:* {tweet}\n\n"
        f"Result: {post_result[:200]}"
    )
    slack.post(msg, channel=slack.X)
    print(f"X afternoon post done — {today.isoformat()}")


if __name__ == "__main__":
    main()
