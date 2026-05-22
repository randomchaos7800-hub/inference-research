#!/usr/bin/env python3
"""Download all 4 missing eval models in parallel to /home/dino/models/."""
import os, time, concurrent.futures
from pathlib import Path
from huggingface_hub import snapshot_download

MODELS = [
    ("nvidia/Qwen3-30B-A3B-NVFP4",     "/home/dino/models/Qwen3-30B-A3B-NVFP4"),
    ("nvidia/Qwen3-32B-NVFP4",          "/home/dino/models/Qwen3-32B-NVFP4"),
    ("Qwen/Qwen3-14B-FP8",              "/home/dino/models/Qwen3-14B-FP8"),
    ("Qwen/Qwen3-30B-A3B-GPTQ-Int4",   "/home/dino/models/Qwen3-30B-A3B-GPTQ-Int4"),
]

def pull(repo_id, local_dir):
    dest = Path(local_dir)
    # Skip if already fully downloaded (has model files)
    if dest.exists() and any(dest.glob("*.safetensors")):
        print(f"[SKIP] {repo_id} — already at {local_dir}")
        return repo_id, True
    print(f"[START] {repo_id} → {local_dir}")
    t0 = time.time()
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            ignore_patterns=["*.bin", "original/*", "*.gguf"],  # skip old-format bins
        )
        elapsed = time.time() - t0
        size = sum(f.stat().st_size for f in Path(local_dir).rglob("*") if f.is_file()) / 1e9
        print(f"[DONE] {repo_id} — {size:.1f} GB in {elapsed/60:.1f} min")
        return repo_id, True
    except Exception as e:
        print(f"[FAIL] {repo_id} — {e}")
        return repo_id, False

print(f"Starting parallel download of {len(MODELS)} models...")
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futs = [pool.submit(pull, r, d) for r, d in MODELS]
    for f in concurrent.futures.as_completed(futs):
        repo, ok = f.result()
        print(f"{'✓' if ok else '✗'} {repo}")

print("All downloads complete.")
