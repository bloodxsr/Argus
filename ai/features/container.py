"""Container Runtime Security — Docker/Podman isolation and kill actions.

Gives the AI engine physical "hands" to quarantine or terminate
compromised containers, not just detect anomalies inside them.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ContainerInfo:
    container_id: str
    name: str
    image: str
    status: str
    pid: int


def _runtime() -> str:
    """Auto-detect whether podman or docker is the active container runtime."""
    for rt in ("podman", "docker"):
        try:
            subprocess.run([rt, "--version"], capture_output=True, check=True, timeout=5)
            return rt
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return "docker"


def list_containers() -> List[ContainerInfo]:
    """List all running containers with their metadata."""
    rt = _runtime()
    try:
        result = subprocess.run(
            [rt, "ps", "--format", "json", "--no-trunc"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []

        raw = result.stdout.strip()
        if not raw:
            return []

        
        containers = []
        if raw.startswith("["):
            entries = json.loads(raw)
        else:
            entries = [json.loads(line) for line in raw.splitlines() if line.strip()]

        for entry in entries:
            containers.append(ContainerInfo(
                container_id=entry.get("Id", entry.get("ID", ""))[:12],
                name=entry.get("Names", entry.get("Name", "unknown")),
                image=entry.get("Image", ""),
                status=entry.get("State", entry.get("Status", "")),
                pid=int(entry.get("Pid", entry.get("pid", 0))),
            ))
        return containers
    except Exception:
        return []


def get_container_for_pid(pid: int) -> Optional[str]:
    """Map a host PID to its container ID by reading /proc/<pid>/cgroup.

    Works for both cgroup v1 and v2. Returns None if the process is not
    running inside a container.
    """
    cgroup_path = f"/proc/{pid}/cgroup"
    try:
        with open(cgroup_path, "r") as f:
            for line in f:
                
                
                for marker in ("docker-", "docker/", "containerd-", "cri-containerd-", "libpod-"):
                    idx = line.find(marker)
                    if idx != -1:
                        raw_id = line[idx + len(marker):].strip().rstrip(".scope").split("/")[0]
                        if len(raw_id) >= 12:
                            return raw_id[:12]
    except FileNotFoundError:
        pass
    return None


def quarantine_container(container_id: str) -> dict:
    """Isolate a container by disconnecting it from ALL networks.

    This prevents lateral movement while preserving the container's
    filesystem state for forensic analysis.
    """
    rt = _runtime()
    result = {"container_id": container_id, "action": "quarantine", "networks_disconnected": []}

    try:
        
        inspect = subprocess.run(
            [rt, "inspect", container_id, "--format", "json"],
            capture_output=True, text=True, timeout=10
        )
        if inspect.returncode != 0:
            result["error"] = f"Container {container_id} not found"
            return result

        data = json.loads(inspect.stdout)
        if isinstance(data, list):
            data = data[0]

        networks = data.get("NetworkSettings", {}).get("Networks", {})

        
        for net_name in networks:
            disconnect = subprocess.run(
                [rt, "network", "disconnect", "--force", net_name, container_id],
                capture_output=True, text=True, timeout=10
            )
            if disconnect.returncode == 0:
                result["networks_disconnected"].append(net_name)

        
        subprocess.run([rt, "pause", container_id], capture_output=True, timeout=10)
        result["status"] = "quarantined"

    except Exception as e:
        result["error"] = str(e)

    return result


def kill_container(container_id: str) -> dict:
    """Force-stop a container immediately."""
    rt = _runtime()
    result = {"container_id": container_id, "action": "kill"}

    try:
        stop = subprocess.run(
            [rt, "kill", "--signal", "SIGKILL", container_id],
            capture_output=True, text=True, timeout=10
        )
        result["status"] = "killed" if stop.returncode == 0 else "failed"
        if stop.returncode != 0:
            result["error"] = stop.stderr.strip()
    except Exception as e:
        result["error"] = str(e)

    return result
