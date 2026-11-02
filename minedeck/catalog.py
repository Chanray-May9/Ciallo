"""硬件 / 币种 / 矿池 / 矿工内核 目录。

数据来源（均为公开资料整理，参考值，非实验室实测）：
- PRL 算力：hashrate.no Pearl benchmarks、PeakMiner 实测档、老矿工算力表
- ETC/RVN/ERG/IRON/NEXA 算力：矿池公开算力表与常见超频档位
- 矿池地址：K1Pool / PearlPool / F2Pool 官方教程页
- 内核参数：SRBMiner-Multi、lolMiner、lpminer 官方文档与矿池教程示例
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------- 显卡算力表
@dataclass
class GPU:
    key: str
    name: str
    vram: int
    tdp: int
    perf: dict            # algo_key -> 算力（已归一化为 H/s）


def _h(th=0.0, gh=0.0, mh=0.0):
    return th * 1e12 + gh * 1e9 + mh * 1e6


# perf 键：prl / etc / rvn / erg / iron / nexa / xna
GPUS = [
    GPU("rtx5090", "RTX 5090", 32, 575, {"prl": _h(th=418), "etc": _h(mh=145), "rvn": _h(mh=75),
                                        "erg": _h(mh=330), "iron": _h(gh=6.2), "nexa": _h(gh=12.0), "xna": _h(mh=75)}),
    GPU("rtx5080", "RTX 5080", 16, 360, {"prl": _h(th=207), "etc": _h(mh=95), "rvn": _h(mh=50),
                                        "erg": _h(mh=240), "iron": _h(gh=4.0), "nexa": _h(gh=8.5), "xna": _h(mh=50)}),
    GPU("rtx5070ti", "RTX 5070 Ti", 16, 300, {"prl": _h(th=171), "etc": _h(mh=78), "rvn": _h(mh=42),
                                             "erg": _h(mh=200), "iron": _h(gh=3.2), "nexa": _h(gh=6.8), "xna": _h(mh=42)}),
    GPU("rtx5070", "RTX 5070", 12, 250, {"prl": _h(th=118), "etc": _h(mh=62), "rvn": _h(mh=34),
                                        "erg": _h(mh=160), "iron": _h(gh=2.6), "nexa": _h(gh=5.4), "xna": _h(mh=34)}),
    GPU("rtx4090", "RTX 4090", 24, 450, {"prl": _h(th=308), "etc": _h(mh=125), "rvn": _h(mh=63),
                                        "erg": _h(mh=280), "iron": _h(gh=4.8), "nexa": _h(gh=8.4), "xna": _h(mh=63)}),
    GPU("rtx4080", "RTX 4080", 16, 320, {"prl": _h(th=159), "etc": _h(mh=88), "rvn": _h(mh=45),
                                        "erg": _h(mh=210), "iron": _h(gh=3.4), "nexa": _h(gh=6.2), "xna": _h(mh=45)}),
    GPU("rtx4070tis", "RTX 4070 Ti Super", 16, 285, {"prl": _h(th=159), "etc": _h(mh=80), "rvn": _h(mh=41),
                                                    "erg": _h(mh=190), "iron": _h(gh=3.1), "nexa": _h(gh=5.6), "xna": _h(mh=41)}),
    GPU("rtx4070s", "RTX 4070 Super", 12, 220, {"prl": _h(th=135), "etc": _h(mh=68), "rvn": _h(mh=35),
                                               "erg": _h(mh=165), "iron": _h(gh=2.7), "nexa": _h(gh=5.0), "xna": _h(mh=35)}),
    GPU("rtx4070", "RTX 4070", 12, 200, {"prl": _h(th=125), "etc": _h(mh=60), "rvn": _h(mh=30),
                                        "erg": _h(mh=145), "iron": _h(gh=2.4), "nexa": _h(gh=4.4), "xna": _h(mh=30)}),
    GPU("rtx4070lap", "RTX 4070 Laptop", 8, 115, {"prl": _h(th=95), "etc": _h(mh=45), "rvn": _h(mh=24),
                                                 "erg": _h(mh=105), "iron": _h(gh=1.8), "nexa": _h(gh=3.2), "xna": _h(mh=24)}),
    GPU("rtx4060ti", "RTX 4060 Ti", 16, 160, {"prl": _h(th=92), "etc": _h(mh=48), "rvn": _h(mh=25),
                                             "erg": _h(mh=120), "iron": _h(gh=1.9), "nexa": _h(gh=3.6), "xna": _h(mh=25)}),
    GPU("rtx4060", "RTX 4060", 8, 115, {"prl": _h(th=65), "etc": _h(mh=34), "rvn": _h(mh=18),
                                       "erg": _h(mh=85), "iron": _h(gh=1.35), "nexa": _h(gh=2.6), "xna": _h(mh=18)}),
    GPU("rtx3090", "RTX 3090", 24, 350, {"prl": _h(th=125), "etc": _h(mh=122), "rvn": _h(mh=62),
                                        "erg": _h(mh=260), "iron": _h(gh=3.6), "nexa": _h(gh=5.2), "xna": _h(mh=62)}),
    GPU("rtx3080ti", "RTX 3080 Ti", 12, 350, {"prl": _h(th=128), "etc": _h(mh=110), "rvn": _h(mh=55),
                                             "erg": _h(mh=235), "iron": _h(gh=3.1), "nexa": _h(gh=4.6), "xna": _h(mh=55)}),
    GPU("rtx3080", "RTX 3080", 10, 320, {"prl": _h(th=107), "etc": _h(mh=95), "rvn": _h(mh=47),
                                        "erg": _h(mh=200), "iron": _h(gh=2.7), "nexa": _h(gh=4.0), "xna": _h(mh=47)}),
    GPU("rtx3070ti", "RTX 3070 Ti", 8, 290, {"prl": _h(th=75), "etc": _h(mh=78), "rvn": _h(mh=39),
                                            "erg": _h(mh=165), "iron": _h(gh=2.2), "nexa": _h(gh=3.3), "xna": _h(mh=39)}),
    GPU("rtx3070", "RTX 3070", 8, 220, {"prl": _h(th=72), "etc": _h(mh=62), "rvn": _h(mh=31),
                                       "erg": _h(mh=140), "iron": _h(gh=1.9), "nexa": _h(gh=2.8), "xna": _h(mh=31)}),
    GPU("rtx3060ti", "RTX 3060 Ti", 8, 200, {"prl": _h(th=60), "etc": _h(mh=60), "rvn": _h(mh=30),
                                            "erg": _h(mh=135), "iron": _h(gh=1.7), "nexa": _h(gh=2.6), "xna": _h(mh=30)}),
    GPU("rtx3060", "RTX 3060", 12, 170, {"prl": _h(th=44), "etc": _h(mh=45), "rvn": _h(mh=23),
                                        "erg": _h(mh=105), "iron": _h(gh=1.25), "nexa": _h(gh=2.0), "xna": _h(mh=23)}),
    GPU("rtx2080ti", "RTX 2080 Ti", 11, 250, {"prl": _h(th=92), "etc": _h(mh=58), "rvn": _h(mh=30),
                                             "erg": _h(mh=110), "iron": _h(gh=1.4), "nexa": _h(gh=2.1), "xna": _h(mh=30)}),
    GPU("h100", "H100 80G", 80, 700, {"prl": _h(th=700), "etc": _h(mh=200), "rvn": _h(mh=120),
                                     "erg": _h(mh=400), "iron": _h(gh=9.5), "nexa": _h(gh=15.0), "xna": _h(mh=120)}),
]

GPU_BY_KEY = {g.key: g for g in GPUS}

# 名称模糊匹配（nvidia-smi 输出 -> key）
GPU_ALIASES = [
    ("5090", "rtx5090"), ("5080", "rtx5080"), ("5070 ti", "rtx5070ti"), ("5070ti", "rtx5070ti"),
    ("5070", "rtx5070"), ("4090", "rtx4090"), ("4080", "rtx4080"), ("4070 ti super", "rtx4070tis"),
    ("4070 super", "rtx4070s"), ("4070 laptop", "rtx4070lap"), ("4070", "rtx4070"),
    ("4060 ti", "rtx4060ti"), ("4060ti", "rtx4060ti"), ("4060", "rtx4060"),
    ("3090", "rtx3090"), ("3080 ti", "rtx3080ti"), ("3080ti", "rtx3080ti"), ("3080", "rtx3080"),
    ("3070 ti", "rtx3070ti"), ("3070ti", "rtx3070ti"), ("3070", "rtx3070"),
    ("3060 ti", "rtx3060ti"), ("3060ti", "rtx3060ti"), ("3060", "rtx3060"),
    ("2080 ti", "rtx2080ti"), ("2080ti", "rtx2080ti"), ("h100", "h100"),
]


# ---------------------------------------------------------------- 矿池
@dataclass
class Pool:
    name: str
    host: str
    port: int
    region: str = "自动"
    fee: str = ""
    note: str = ""
    wallet_mode: str = "address"     # address = 直接填币地址；account = 需填矿池账户名
    scheme: str = ""                 # PPLNS / PPS / SOLO
    payout: str = ""                 # 打款周期
    minimum: str = ""                # 最低起付
    confirm: str = ""                # 到账前确认数
    desc: str = ""                   # 详细介绍
    url: str = ""                    # 官网/教程
    coins: tuple = ()                # 该池支持的币种（用于兼容性提示）


K1_COINS = ("PRL", "ETC", "RVN", "ERG", "ALPH", "KAS", "XEL", "ZEPH", "ZANO", "QUAI", "OCTA")
F2_COINS = ("PRL", "ETC", "RVN", "ERG", "KAS", "ALPH", "BTC", "LTC", "ETHW")


POOLS = {
    "PRL": [
        Pool("K1Pool 中国", "cn.pearl.k1pool.com", 3360, "中国", "1%", "国内直连延迟低",
             scheme="PPLNS", payout="每 12 小时自动打款", minimum="1 PRL（可调）", confirm="100 确认成熟",
             desc="俄系老牌多币池，PRL 有中国 / 欧洲 / 美国三地节点，国内延迟最低。"
                  "PPLNS 按最近 20 万个份额结算，1% 费率，每 720 分钟自动打款，"
                  "注册后可在 Wallets 页把起付门槛调高。区块需要 100 个确认（约 5 小时）才从"
                  "「未确认余额」变成可提现。",
             url="https://k1pool.org/zh/pool/pearl", coins=K1_COINS),
        Pool("K1Pool 欧洲", "eu.pearl.k1pool.com", 3360, "欧洲", "1%", "国内延迟略高",
             scheme="PPLNS", payout="每 12 小时自动打款", minimum="1 PRL（可调）", confirm="100 确认成熟",
             desc="同一矿池的欧洲节点，结算、费率、门槛与中国节点一致，适合没有国内节点时的备用线路。",
             url="https://k1pool.org/zh/pool/pearl", coins=K1_COINS),
        Pool("K1Pool 美国", "us.pearl.k1pool.com", 3360, "美国", "1%", "跨洋线路",
             scheme="PPLNS", payout="每 12 小时自动打款", minimum="1 PRL（可调）", confirm="100 确认成熟",
             desc="美国节点，国内连接延迟偏高、份额容易变 stale，一般只作为第三条备用线。",
             url="https://k1pool.org/zh/pool/pearl", coins=K1_COINS),
        Pool("PearlPool", "pearlpool.cloud", 5566, "欧洲", "0.5%", "免注册，钱包即身份",
             scheme="PPLNS", payout="达门槛自动打款", minimum="2 PRL", confirm="以站内公告为准",
             desc="社区自建的 PRL 专池，费率全场最低 0.5%，不需要注册——钱包地址就是账户，"
                  "矿工名写成「钱包.rig01」即可。属于公开 beta，池子总算力小、出块运气波动大，"
                  "适合小额先试水或分散风险。",
             url="https://pearlpool.cloud", coins=("PRL",)),
        Pool("F2Pool（需账户名）", "pearl.f2pool.com", 5500, "自动", "1%", "填矿池账户名，不是钱包地址",
             wallet_mode="account", scheme="PPS", payout="每天 UTC 00:00–08:00", minimum="1 PRL",
             confirm="打款后需链上确认",
             desc="国内老牌矿池，PRL 用 PPS 结算：每个有效份额直接折算成钱，不看池子当天运气，"
                  "收益最稳但也拿不到「幸运块」的超额。1% 费率，每天 UTC 00:00–08:00"
                  "（北京时间 08:00–16:00）统一打款，1 PRL 起付。注意是账户名挖矿，"
                  "填钱包地址会挖空。",
             url="https://www.f2pool.com", coins=F2_COINS),
        Pool("自定义矿池", "", 0, "自定义", "", "手动填写 host:port",
             desc="填任意 PRL 矿池的 host 和端口，钱包格式按该矿池要求填。"),
    ],
    "ETC": [
        Pool("K1Pool 中国", "cn.etc.k1pool.com", 3821, "中国", "1%", "etchash 算法",
             scheme="PPLNS", payout="每 12 小时自动打款", minimum="见矿池页面", confirm="",
             desc="K1Pool 的 ETC 池，etchash 算法，国内节点延迟低。ETC 现在由 ASIC 主导，"
                  "显卡只能挖到零头，更适合顺手挂着。",
             url="https://k1pool.org/zh/pool/etc", coins=K1_COINS),
        Pool("K1Pool 欧洲", "eu.etc.k1pool.com", 3821, "欧洲", "1%", "etchash 算法",
             scheme="PPLNS", payout="每 12 小时自动打款", minimum="见矿池页面", confirm="",
             desc="欧洲节点，规则同中国节点，国内连接延迟高一些。",
             url="https://k1pool.org/zh/pool/etc", coins=K1_COINS),
        Pool("自定义矿池", "", 0, "自定义", "", "手动填写 host:port",
             desc="填任意 ETC 矿池（2Miners、Hiveon、Kryptex 等）的 host 和端口。"),
    ],
    "RVN": [
        Pool("K1Pool 中国", "cn.rvn.k1pool.com", 7861, "中国", "1%", "kawpow 算法",
             scheme="PPLNS", payout="每 12 小时自动打款", minimum="见矿池页面", confirm="",
             desc="KawPow 算法池，国内节点，PPLNS 结算 1% 费率。RVN 出块 1 分钟、收益偏低，"
                  "主要看电价，适合低电价的机器顺手挂。",
             url="https://k1pool.org/zh/pool/rvn", coins=K1_COINS),
        Pool("K1Pool 欧洲", "eu.rvn.k1pool.com", 7861, "欧洲", "1%", "kawpow 算法",
             scheme="PPLNS", payout="每 12 小时自动打款", minimum="见矿池页面", confirm="",
             desc="欧洲节点，规则同中国节点。",
             url="https://k1pool.org/zh/pool/rvn", coins=K1_COINS),
        Pool("自定义矿池", "", 0, "自定义", "", "手动填写 host:port",
             desc="填任意 RVN 矿池的 host 和端口。"),
    ],
    "KAS": [
        Pool("K1Pool 中国 (GPU)", "cn.kaspa.k1pool.com", 3112, "中国", "1%", "kheavyhash"),
        Pool("自定义矿池", "", 0, "自定义", "", "手动填写 host:port"),
    ],
    "ERG": [Pool("自定义矿池", "", 0, "自定义", "", "k1pool / woolypooly / 2miners 均可")],
    "IRON": [Pool("自定义矿池", "", 0, "自定义", "", "需自行填写矿池 host:port")],
    "NEXA": [Pool("自定义矿池", "", 0, "自定义", "", "需自行填写矿池 host:port")],
    "XNA": [Pool("自定义矿池", "", 0, "自定义", "", "需自行填写矿池 host:port")],
}


# ---------------------------------------------------------------- 币种
@dataclass
class Coin:
    symbol: str
    name: str
    name_cn: str
    algo_key: str          # GPU.perf 的键
    algo: str              # 算法显示名
    wm_tag: str            # whattomine tag
    unit: str              # 算力显示单位
    color: str
    digits: int = 4
    note: str = ""
    tags: list = field(default_factory=list)
    custom: bool = False
    data: dict = field(default_factory=dict)


COINS = [
    Coin("PRL", "Pearl", "珍珠币", "prl", "PearlHash", "PRL", "TH/s", "#6C5CE7", 4,
         "AI 矩阵算力 PoW，当前显卡收益第一梯队", ["主推"]),
    Coin("ETC", "Ethereum Classic", "以太经典", "etc", "Etchash", "ETC", "MH/s", "#22A06B", 4,
         "老牌显卡币，DAG 稳定，内核兼容性最好"),
    Coin("RVN", "Ravencoin", "渡鸦币", "rvn", "KawPow", "RVN", "MH/s", "#3452B4", 3,
         "KawPow 算法，功耗偏高，适合低电价"),
    Coin("ERG", "Ergo", "尔格", "erg", "Autolykos2", "ERG", "MH/s", "#F1731F", 3,
         "显存友好，8G 卡可长期跑"),
    Coin("IRON", "Iron Fish", "铁鱼", "iron", "FishHash", "IRON", "GH/s", "#8A6D3B", 4,
         "全网只有 ~68 GH/s，单卡占比高；流动性差，注意卖出滑点"),
    Coin("NEXA", "Nexa", "内克萨", "nexa", "NexaPow", "NEXA", "GH/s", "#0E9F6E", 1,
         "高产出低单价，钱包归集注意精度"),
    Coin("XNA", "Neurai", "纽莱", "xna", "KawPow", "XNA", "MH/s", "#0E7490", 2,
         "KawPow 系小币，波动大"),
]

COIN_BY_SYMBOL = {c.symbol: c for c in COINS}


def coin_from_custom(d):
    """把配置里的自定义币种 dict 变成 Coin 对象。"""
    sym = (d.get("symbol") or "CUS").upper()
    return Coin(
        symbol=sym,
        name=d.get("name") or sym,
        name_cn=d.get("name") or "自定义币种",
        algo_key="custom",
        algo=d.get("algo") or "自定义算法",
        wm_tag="",
        unit=d.get("unit") or "MH/s",
        color=d.get("color") or "#7C3AED",
        digits=2,
        note="自定义币种 · 参数由你填写",
        tags=["自定义"],
        custom=True,
        data=d,
    )

UNIT_DIV = {"H/s": 1.0, "KH/s": 1e3, "MH/s": 1e6, "GH/s": 1e9, "TH/s": 1e12}


def fmt_hash(h):
    """把 H/s 格式化成带单位字符串。"""
    for unit, div in (("TH/s", 1e12), ("GH/s", 1e9), ("MH/s", 1e6), ("KH/s", 1e3)):
        if h >= div:
            return f"{h / div:,.2f} {unit}"
    return f"{h:,.0f} H/s"


# ---------------------------------------------------------------- 矿工内核
@dataclass
class Miner:
    key: str
    name: str
    exe: str
    repo: str = ""              # github owner/repo，用于解析最新资产
    asset_hint: str = ""        # 资产名包含的关键词
    direct_urls: list = field(default_factory=list)
    homepage: str = ""
    note: str = ""


MINERS = {
    "lpminer": Miner(
        "lpminer", "lpminer", "lpminer.exe",
        direct_urls=["https://pearl.luckypool.io/lpminer/lpminer-0.1.10.zip"],
        homepage="https://pearl.luckypool.io",
        note="Pearl 社区内核，专为 PRL 优化，体积小"),
    "srbminer": Miner(
        "srbminer", "SRBMiner-Multi", "SRBMiner-MULTI.exe",
        repo="doktor83/SRBMiner-Multi", asset_hint="win64",
        direct_urls=["https://github.com/doktor83/SRBMiner-Multi/releases/download/3.8.3/SRBMiner-Multi-3-8-3-win64.zip"],
        homepage="https://github.com/doktor83/SRBMiner-Multi",
        note="多算法内核，PearlHash 官方推荐之一"),
    "lolminer": Miner(
        "lolminer", "lolMiner", "lolMiner.exe",
        repo="Lolliedieb/lolMiner-releases", asset_hint="Win64.zip",
        direct_urls=["https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.98a/lolMiner_v1.98a_Win64.zip"],
        homepage="https://github.com/Lolliedieb/lolMiner-releases",
        note="ETC/RVN/ERG/IRON/NEXA 兼容性最好的内核"),
}

# 币种 -> 首选内核
COIN_MINER = {
    "PRL": "lpminer",
    "ETC": "lolminer",
    "RVN": "lolminer",
    "ERG": "lolminer",
    "IRON": "lolminer",
    "NEXA": "lolminer",
    "XNA": "lolminer",
}

# 币种 -> 实际支持该算法的内核（兼容性差异就在这里）
COIN_MINERS = {
    "PRL": ["lpminer", "srbminer"],
    "ETC": ["lolminer", "srbminer"],
    "RVN": ["lolminer", "srbminer"],
    "ERG": ["lolminer", "srbminer"],
    "IRON": ["lolminer"],
    "NEXA": ["lolminer"],
    "XNA": ["lolminer", "srbminer"],
}
ALL_MINER_KEYS = ["lolminer", "srbminer", "lpminer"]


def miners_for(coin):
    """该币种可用的内核列表；自定义币种全部列出，由用户确认算法支持。"""
    if coin.custom:
        return list(ALL_MINER_KEYS)
    return COIN_MINERS.get(coin.symbol, list(ALL_MINER_KEYS))

# 币种 -> 内核算法参数
MINER_ALGO = {
    "PRL": {"lpminer": ["--algo", "pearl"], "srbminer": ["--algorithm", "pearlhash"]},
    "ETC": {"lolminer": ["--algo", "ETCHASH"], "srbminer": ["--algorithm", "etchash"]},
    "RVN": {"lolminer": ["--algo", "KAWPOW"], "srbminer": ["--algorithm", "kawpow"]},
    "ERG": {"lolminer": ["--algo", "AUTOLYKOS2"], "srbminer": ["--algorithm", "autolykos2"]},
    "IRON": {"lolminer": ["--algo", "IRONFISH"]},
    "NEXA": {"lolminer": ["--algo", "NEXA"]},
    "XNA": {"lolminer": ["--algo", "KAWPOW"], "srbminer": ["--algorithm", "kawpow"]},
}


def build_args(coin: Coin, miner_key: str, host: str, port: int, wallet: str, worker: str, extra: str = ""):
    """按真实内核语法拼命令行参数。"""
    if coin.custom:
        algo = (coin.data.get("algo_arg") or "").strip()
        target = f"{host}:{port}"
        who = f"{wallet}.{worker}" if worker else wallet
        if miner_key == "lpminer":
            args = ["--algo", algo or "custom", "--pool", f"stratum+tcp://{target}", "--wallet", who]
        elif miner_key == "srbminer":
            args = ["--algorithm", algo or "custom", "--pool", target, "--wallet", who, "--disable-cpu"]
        else:
            args = ["--algo", (algo or "custom").upper(), "--pool", target, "--user", who]
        if extra.strip():
            args += extra.split()
        return args

    algo_args = MINER_ALGO.get(coin.symbol, {}).get(miner_key)
    if not algo_args:
        return None
    target = f"{host}:{port}"
    who = f"{wallet}.{worker}" if worker else wallet

    if miner_key == "lpminer":
        args = ["--algo", "pearl", "--pool", f"stratum+tcp://{target}", "--wallet", who]
    elif miner_key == "srbminer":
        args = algo_args + ["--pool", target, "--wallet", who, "--disable-cpu"]
    else:  # lolminer
        args = algo_args + ["--pool", target, "--user", who]
    if extra.strip():
        args += extra.split()
    return args


def pools_for(coin):
    """币种可用矿池；自定义币种使用其配置里的矿池。"""
    if coin.custom:
        host = coin.data.get("pool_host") or ""
        port = int(coin.data.get("pool_port") or 0)
        out = []
        if host and port:
            out.append(Pool("自定义矿池", host, port, "自定义", "", "来自币种配置"))
        out.append(Pool("自定义矿池", "", 0, "自定义", "", "手动填写 host:port"))
        return out
    return POOLS.get(coin.symbol, [Pool("自定义矿池", "", 0, "自定义", "", "手动填写 host:port")])



# 官方教程 / 参考资料（设置页与开挖页展示）
REFERENCES = [
    ("K1Pool · Pearl 挖矿教程（含国内 CN 节点）", "https://k1pool.org/zh/pool/pearl/how-to-start"),
    ("F2Pool · PRL 挖矿教程（内核参数与合并挖矿）", "https://f2pool.zendesk.com/hc/zh-tw/articles/59248379419417"),
    ("PearlPool · PRL 矿池（0.5% 费率，免注册）", "https://pearlpool.cloud"),
    ("hashrate.no · PRL 逐卡算力与实时收益", "https://www.hashrate.no/coins/PRL/benchmarks"),
    ("91挖 · PRL 超频参数与算力表", "https://91wa.net/prl-pearl-gpu-overclocking-hashrate-table/"),
    ("SRBMiner-Multi · GitHub Releases", "https://github.com/doktor83/SRBMiner-Multi/releases"),
    ("lolMiner · GitHub Releases", "https://github.com/Lolliedieb/lolMiner-releases/releases"),
    ("lpminer · Pearl 社区内核", "https://pearl.luckypool.io/lpminer/"),
]
