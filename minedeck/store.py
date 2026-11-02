"""配置持久化。"""

import json
import os
from dataclasses import dataclass, asdict, field


@dataclass
class Config:
    electricity: float = 0.60          # 元 / 度（可选，默认不扣）
    use_electricity: bool = False      # 默认只看毛收益
    currency: str = "CNY"
    usd_cny: float = 7.10
    refresh_sec: int = 30
    price_refresh_sec: int = 3
    gpu_key: str = ""                  # 空 = 自动检测
    power_limit: int = 0               # 0 = 跟随检测/默认
    perf_pct: int = 100                # 显卡性能占用百分比 30-100
    limit_power: bool = False          # 开挖时按占用率限制功耗（需管理员）
    unit: str = "天"
    selected_coin: str = "PRL"
    worker: str = "rig01"
    wallets: dict = field(default_factory=dict)        # symbol -> address
    hash_overrides: dict = field(default_factory=dict)  # symbol -> H/s（实测校准）
    miner_paths: dict = field(default_factory=dict)     # miner key -> exe path
    miner_choice: dict = field(default_factory=dict)     # 币种 -> 选中的内核 key
    extra_args: str = ""
    custom_coins: list = field(default_factory=list)    # 自定义币种定义
    history: list = field(default_factory=list)         # [[ts, revenue_day_cny], ...]
    history_base: str = "PRL4"                         # 曲线基准币种（改版本号会重置曲线）


def _path(app_dir):
    return os.path.join(app_dir, "data", "config.json")


def load(app_dir):
    p = _path(app_dir)
    cfg = Config()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        except Exception:
            pass
    return cfg


def save(app_dir, cfg):
    p = _path(app_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

