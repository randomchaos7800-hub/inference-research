# vLLM Upgrade Attempt + Recovery — 2026-05-10

**Hardware:** 2× RTX 5060 Ti 16GB GDDR7, Blackwell SM_120, Intel Core Ultra 7 265F, MSI MAG Z890 Tomahawk  
**Stack:** vLLM 0.19.2rc1.dev228+gebf862c35 (Genesis custom patched), Qwen3.6-27B-int4-AutoRound, GPTQ-Marlin, TP=2  
**Trigger:** DFlash research → confirmed not applicable → investigated vLLM 0.20.1 upgrade path  

---

## Background

Investigated DFlash (block diffusion speculative decoding). Confirmed it does not apply to Genesis:
- Genesis uses **self-MTP** (Qwen3 native prediction heads, same forward pass, zero overhead)
- DFlash replaces an *external* draft model — Genesis has no external draft model
- Disabling MTP causes ~50% throughput regression (verified 2026-05-09)
- DFlash would add a separate model on top of what self-MTP already does for free

Identified vLLM 0.20.2 as potentially beneficial (SM_120 CUTLASS fixes). Proceeded with upgrade.

---

## Upgrade Attempt: vLLM 0.19.2rc1 → 0.20.2

### Process
1. Saved `pip freeze` backup to `~/vllm-pre-upgrade.txt`
2. Tarred full vLLM site-packages to `~/vllm-backup-0.19.2rc1-dev228.tar.gz` (241MB)
3. `pip install --upgrade --pre vllm --extra-index-url https://wheels.vllm.ai/nightly` → installed 0.20.2
4. Recreated `_genesis` symlink (pip upgrade wipes it — expected, documented in INSTALL.md)
5. Ran `python3 -m vllm._genesis.patches.apply_all` → 23 applied, 36 skipped, 0 failed
6. Restarted vllm-genesis

### Result: FAILED — NCCL crash on TP=2 init

```
RuntimeError: NCCL error: unhandled cuda error (run with NCCL_DEBUG=INFO for details)
Exception: WorkerProc initialization failed due to an exception in a background process.
```

The service entered a crash-loop. vLLM 0.20.2 fails to initialize multi-GPU NCCL on Blackwell SM_120 (RTX 5060 Ti). This is a known upstream compatibility gap — SM_120 support in 0.20.x is incomplete for TP>1.

The crash-loop caused GPU VRAM to not release between restart attempts (CUDA contexts stuck), which then blocked the rollback.

---

## Rollback: 0.20.2 → 0.19.2rc1

### Process
1. `systemctl --user stop vllm-genesis`
2. Killed zombie vLLM processes (PIDs holding ~15GB VRAM each)
3. Waited for VRAM to clear to baseline (<500 MiB)
4. `pip uninstall vllm`
5. `tar -xzf ~/vllm-backup-0.19.2rc1-dev228.tar.gz -C /opt/ai/vllm-env/lib/python3.12/site-packages`
6. Recreated `/opt/ai/vllm-env/bin/vllm` entry point (uninstall removes it, tar restore doesn't recreate it)
7. Confirmed `python3 -c 'import vllm; print(vllm.__version__)'` → `0.19.2rc1.dev228+gebf862c35`

### Complication: Kernel Upgrade During Reboot

During recovery, the system was rebooted. The running kernel was `6.17.0-22-generic`; apt had staged `6.17.0-23-generic` which booted by default. NVIDIA modules do not exist for `-23` (requires `nvidia-kernel-common-580 >= 580.142`, only `580.126.09` installed). System came up with no NVIDIA driver.

**Fix:** Pinned GRUB default to `6.17.0-22-generic`:
```bash
sudo sed -i 's/^GRUB_DEFAULT=.*/GRUB_DEFAULT="Advanced options for Ubuntu>Ubuntu, with Linux 6.17.0-22-generic"/' /etc/default/grub
sudo update-grub
sudo reboot
```

### Complication: Headless Boot Failure

Tower is headless (no monitor attached). Intel Core Ultra 7 265F has no iGPU. MSI MAG Z890 Tomahawk halts POST when no display is detected with an F-series CPU. Required physical monitor + keyboard to reach BIOS and diagnose.

**BIOS state confirmed:** AC Power Recovery = Power On (already correct). ErP was enabled (kills WoL standby power) → disabled. Resume by PCI-E/Network device enabled for Wake-on-LAN.

**Root cause of initial plug-cycle failure:** TPLink smart plug switches in <100ms — too fast for the board to register AC loss. The board capacitors held charge; no power-restore event was triggered. Need 3+ seconds off for proper AC loss detection.

**Pending fix:** Dummy HDMI/DisplayPort adapter — eliminates headless POST halt permanently.

---

## Post-Recovery Benchmark

| Metric | Baseline (2026-05-06/09) | Post-Recovery (2026-05-10) |
|---|---|---|
| Throughput | 79.44–80.8 t/s | 71.4 t/s |
| Kernel | 6.17.0-22 | 6.17.0-22 |
| vLLM | 0.19.2rc1.dev228 | 0.19.2rc1.dev228 |
| Genesis patches | 32 applied | 32 applied |

~10% throughput regression post-recovery. Likely causes: Triton JIT cache partially invalidated by the 0.20.2 run, CUDA graph warm-up time after multiple forced kills. Expected to normalize after sustained operation.

---

## Hard Rules From This Incident

| Rule | Reason |
|---|---|
| **Do NOT upgrade to vLLM 0.20.x on SM_120 TP=2** | NCCL init crash, service enters unrecoverable crash-loop |
| **Always tar backup vLLM before upgrading** | pip uninstall + tar restore is the only safe rollback path (no nightly wheel cache) |
| **After killing vLLM, wait for VRAM < 500 MiB before restart** | CUDA contexts persist after process death; new instance OOMs at startup |
| **Kernel pin to 6.17.0-22 until nvidia-kernel-common >= 580.142 is in repos** | 6.17.0-23 boots but has no NVIDIA driver |
| **TPLink plug cycle needs 3+ seconds off** | < 1s doesn't register as AC loss on Z890 Tomahawk |
| **mollydog bootstrap works over SSH** | `~/bin/mollydog` uses the bootstrap sudoers rule — no interactive terminal needed |

---

## Operational Notes

- `_genesis` symlink is wiped on every `pip install/uninstall vllm` — must be recreated at `/opt/ai/vllm-env/lib/python3.12/site-packages/vllm/_genesis → /opt/ai/vendor/genesis-vllm-patches/vllm/_genesis`
- `vllm` binary entry point is also wiped by uninstall — recreate with `printf '#!/opt/ai/vllm-env/bin/python3\nimport re, sys\nfrom vllm.entrypoints.cli.main import main\nif __name__ == "__main__": sys.argv[0] = re.sub(r"(-script\\.pyw|\\.exe)?$", "", sys.argv[0]); sys.exit(main())\n' > /opt/ai/vllm-env/bin/vllm && chmod +x /opt/ai/vllm-env/bin/vllm`
- Genesis patch apply is idempotent — safe to run multiple times

---

## Conclusion

vLLM 0.20.2 is not viable for this stack. Stay on 0.19.2rc1. Monitor genesis-vllm-patches repo for explicit SM_120 + TP=2 support notes before retrying any upgrade.

Genesis is operational at 71 t/s (normalizing). No data loss, no configuration loss.
