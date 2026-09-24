#!/usr/bin/env python3
"""Run the LongMemEval harness with Mike's primary inference pointed at another
OpenAI-compatible endpoint, without touching config/settings.json (live Mike
keeps his own). Everything else (memory, tools, judge) is the real relay.

    EVAL_BASE_URL=https://api.anthropic.com/v1/ EVAL_MODEL=claude-sonnet-5 \
    EVAL_API_KEY=$(vault get anthropic_api_key) \
    python tests/longmemeval/run_with_model.py --limit 25 --tasks single-session-user --no-extract
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import relay.switchboard as sb
from openai import OpenAI

_orig_init = sb.Switchboard.__init__

def _patched_init(self, *a, **kw):
    _orig_init(self, *a, **kw)
    url, model, key = os.environ.get("EVAL_BASE_URL"), os.environ.get("EVAL_MODEL"), os.environ.get("EVAL_API_KEY", "local")
    if url and model:
        self.pod_client = OpenAI(base_url=url, api_key=key)
        self.pod_model = model
        self.MODEL = model
        self.POD_URL = url
        self.prefer_openrouter = False
        self.openrouter_client = None  # no silent fallback to a different model mid-eval
        sb.logger.warning(f"EVAL override: primary inference -> {url} model={model}, OpenRouter fallback disabled")

sb.Switchboard.__init__ = _patched_init

# relay.py overrides the model per turn (terra for non-IRC users); an eval
# against another provider must pin every turn to EVAL_MODEL.
_orig_call = sb.Switchboard.call
def _patched_call(self, *a, **kw):
    if os.environ.get("EVAL_MODEL"):
        kw["model_override"] = None
    return _orig_call(self, *a, **kw)
sb.Switchboard.call = _patched_call
sys.argv[0] = str(Path(__file__).with_name("runner.py"))
import runpy
runpy.run_path(str(Path(__file__).with_name("runner.py")), run_name="__main__")
