"""显卡检测：nvidia-smi 优先，退化为 Windows WMI。"""

import subprocess
from dataclasses import dataclass

from .catalog import GPU_ALIASES, GPU_BY_KEY


@dataclass
class GPUInfo:
    name: str
    vram: int
    power_limit: int
    key: str
    source: str

    @property
    def model(self):
        from .catalog import GPU_BY_KEY
        return GPU_BY_KEY.get(self.key)


def _run(cmd, timeout=8):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return out.stdout.strip()
    except Exception:
        return ""


def match_key(name):
    low = (name or "").lower()
    for alias, key in GPU_ALIASES:
        if alias in low:
            return key
    return ""


def detect():
    raw = _run(["nvidia-smi", "--query-gpu=name,memory.total,power.limit",
                "--format=csv,noheader,nounits"])
    if raw:
        first = raw.splitlines()[0]
        parts = [p.strip() for p in first.split(",")]
        name = parts[0] if parts else "NVIDIA GPU"
        vram = int(float(parts[1])) // 1024 if len(parts) > 1 and parts[1].replace(".", "").isdigit() else 0
        power = int(float(parts[2])) if len(parts) > 2 and parts[2].replace(".", "").isdigit() else 0
        key = match_key(name)
        if not key and power:
            key = "rtx4070lap" if "laptop" in name.lower() else ""
        return GPUInfo(name, vram, power, key, "nvidia-smi")

    # 退化：WMI
    ps = _run(["powershell", "-NoProfile", "-Command",
               "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"])
    for line in (ps or "").splitlines():
        n = line.strip()
        if not n:
            continue
        key = match_key(n)
        if key or "nvidia" in n.lower():
            return GPUInfo(n, 0, 0, key, "wmi")
    return GPUInfo("未检测到 NVIDIA 显卡", 0, 0, "", "none")


def default_power(key, detected_power):
    if detected_power and detected_power > 20:
        return detected_power
    g = GPU_BY_KEY.get(key)
    if g:
        return int(g.tdp * 0.8)
    return 120
