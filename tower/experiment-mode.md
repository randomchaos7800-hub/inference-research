# Tower Experiment Mode

This is the hard-lock protocol for tower inference research.

Use it before any benchmark that might touch the production inference path.

## Enter

```bash
python3 /home/dino/scripts/tower-experiment-lock.py lock --minutes 180 --reason "<reason>"
```

This:

1. sets tower research mode
2. switches `local-proxy` to `openrouter`
3. stops and SIGKILLs `vllm-backend.service` if needed
4. runtime-masks `vllm-backend.service`
5. verifies the GPUs are actually clear

## Exit

```bash
python3 /home/dino/scripts/tower-experiment-lock.py unlock
```

This clears the lock and restores `genesis`.

## Rule

- Do not use `model=local` during experiment mode unless you intentionally want OpenRouter traffic
- Do not treat a stopped unit as enough; verify GPU state
- Benchmark candidates directly on their own URL while the lock is active
