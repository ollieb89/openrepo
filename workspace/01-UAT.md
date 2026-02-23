# User Acceptance Testing (UAT): Phase 1 - Environment Substrate

**Date:** 2026-02-17
**Phase Goal:** Establish the physical and networking foundation for the swarm.

## Test Summary

| Test ID | Feature | Description | Status |
| :--- | :--- | :--- | :--- |
| UAT-1.1 | Gateway Health | Verify Gateway is listening on port 18789 and returns 200 OK. | PASS |
| UAT-1.2 | Config Integrity | Verify `openclaw.json` contains `maxConcurrent` and `subagents.maxConcurrent`. | PASS |
| UAT-1.3 | Physical Isolation | Verify agent container cannot access host files outside its mount. | PASS |
| UAT-1.4 | GPU Passthrough | Verify Nvidia GPU is accessible from within a Docker container. | PASS |

---

## Test Details

### UAT-1.1: Gateway Health
- **Method:** `curl -I http://localhost:18789`
- **Expected:** HTTP/1.1 200 OK
- **Result:** PASS
- **Notes:** Gateway responded with 200 OK.

### UAT-1.2: Config Integrity
- **Method:** `cat openclaw.json | grep maxConcurrent`
- **Expected:** `maxConcurrent: 4` and `subagents.maxConcurrent: 8`
- **Result:** PASS
- **Notes:** Config correctly contains the required concurrency limits.

### UAT-1.3: Physical Isolation
- **Method:** Run a test container and attempt to `ls /home/ollie` (which should not be mounted).
- **Expected:** Error: "No such file or directory" or "Permission denied" if blocked correctly.
- **Result:** PASS
- **Notes:** Container correctly reported "No such file or directory" when attempting to access host home directory.

### UAT-1.4: GPU Passthrough
- **Method:** `docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi`
- **Expected:** Successful output of `nvidia-smi` showing the RTX 3070 Ti.
- **Result:** PASS
- **Notes:** Verified after remediation (installed nvidia-container-toolkit 1.18.2-1 and configured Docker runtime). GPU is accessible from within containers.
