# Remediation Plan: UAT-1.4 GPU Passthrough Failure

## Diagnosis
The migration from Snap Docker to native Docker (CE) successfully resolved isolation issues (SEC-01) but failed to re-establish the Nvidia Container Toolkit integration.
- `nvidia-smi` works on host.
- `nvidia-container-toolkit` is NOT installed.
- `/etc/docker/daemon.json` is missing.

## Fix Plan
1. **Install Nvidia Container Toolkit:**
   ```bash
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg 
     && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | 
       sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | 
       sudo tee /etc/docker/daemon.json /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   ```
2. **Configure Docker Runtime:**
   ```bash
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```
3. **Verification:**
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
   ```

## Next Steps
Execute this plan via `/gsd:execute-phase` or manual intervention to restore GPU capability for the swarm.
