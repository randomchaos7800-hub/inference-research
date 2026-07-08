# Tower Experiment Mode

This is the hard-lock protocol for tower inference research.

Goal:
- keep the fleet entrypoint alive
- prevent `genesis` from intruding during experiments
- make accidental `model=local` traffic land on `openrouter`, not on local GPUs
- refuse to proceed unless the production backend is actually off the cards

## Enter

Use:

```bash
python3 /home/dino/scripts/tower-experiment-lock.py lock --minutes 180 --reason "<reason>"
```

That does all of the following:

1. sets tower research mode so recovery/watchdog logic stands down
2. switches `local-proxy` to `openrouter`
3. stops `vllm-backend.service`
4. SIGKILLs lingering backend workers if needed
5. runtime-masks `vllm-backend.service`
6. verifies the GPU is clear enough to benchmark

## Exit

Use:

```bash
python3 /home/dino/scripts/tower-experiment-lock.py unlock
```

That clears research mode, unmasks `vllm-backend.service`, and restores `genesis`.

## Rules

- Do not start an experiment unless the lock helper reports `proxy_active: openrouter`
- Do not benchmark `model=local` during experiment mode unless you explicitly want OpenRouter traffic
- Do not rely on a stopped service alone; the lock must also be verified by GPU state
- If the lock is active, use direct candidate URLs for the experiment path

## Status

Use:

```bash
python3 /home/dino/scripts/tower-experiment-lock.py status
```

The status report should show:

- research mode active
- proxy active backend `openrouter`
- no compute apps on the GPUs
- low GPU memory usage
