# Codex Case Law
**Purpose:** durable patterns Codex should remember because they changed outcomes materially.

---

## [BIG UNLOCK] Artifact Verification Beats "It Ran"

**When:** Repeated infra and agent sessions on `cha0tikhome`, especially cron, dashboard, backup, and inference-monitor work.

**Old instinct:** Check whether the service is active, the cron exists, or the command exited `0`, then move on.

**Failure mode:** The mechanism can be healthy while the actual deliverable is missing, stale, or wrong.

Examples seen on this machine:
- cron job executed but wrote nothing useful
- dashboard showed green while the underlying job was erroring
- inference status existed but reflected alias state rather than the real backend/model
- backup scripts existed and were scheduled, but target directories were wrong so the real backup never happened

**Unlock:** Verify the artifact that the mechanism is supposed to produce.

For this machine, that means checking things like:
- did the output file get updated
- did the backup archive get created and contain expected files
- did the dashboard show the real live model and fresh timestamp
- did the post, message, or report actually land
- did the restore drill prove the backup can be extracted

**Pattern:** Delivery truth beats execution truth.

**Codex rule:** When the task involves automation, scheduled work, monitoring, publishing, backups, or synchronization, do not stop at "service active" or "command succeeded." Verify the end artifact directly.
