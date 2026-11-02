"""行情与网络数据：whattomine + CoinGecko + CoinPaprika，带本地缓存与离线兜底。"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field


UA = {"User-Agent": "MineDeck/1.0 (+local mining dashboard)"}
WT_URL = "https://whattomine.com/coins.json"
BTC_SOURCES = [
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
    "https://api.coinpaprika.com/v1/tickers/btc-bitcoin",
    "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
]
PRL_URL = "https://api.coinpaprika.com/v1/tickers/prl-pearl-1"

# whattomine 的 BTC 折算价对低价币会因精度截断而失真，这里用 CoinGecko 现货价校正
CG_IDS = {
    "PRL": "pearl-2",
    "ETC": "ethereum-classic",
    "RVN": "ravencoin",
    "ERG": "ergo",
    "IRON": "iron-fish",
    "NEXA": "nexacoin",
    "XNA": "neurai",
}


def _apply_coingecko(md, data):
    """data 为 /coins/markets 的结果：价格、涨跌、成交额、市值一次补齐。"""
    if not data:
        return 0
    hit = 0
    for tag, cid in CG_IDS.items():
        row = data.get(cid)
        if not row or tag not in md.coins:
            continue
        try:
            md.coins[tag].price_usd = float(row["current_price"])
            if row.get("price_change_percentage_24h") is not None:
                md.coins[tag].change_24h = float(row["price_change_percentage_24h"])
            md.coins[tag].volume_24h = float(row.get("total_volume") or 0)
            md.coins[tag].market_cap = float(row.get("market_cap") or 0)
            hit += 1
        except (KeyError, TypeError, ValueError):
            continue
    return hit


def _coingecko_prices():
    ids = ",".join(sorted(set(CG_IDS.values())))
    url = ("https://api.coingecko.com/api/v3/simple/price?ids=" + ids +
           "&vs_currencies=usd&include_24hr_change=true")
    try:
        return _get_json(url, timeout=12)
    except Exception:
        return None


def _coingecko_markets():
    """一次拿到价格 / 涨跌 / 24h 成交额 / 市值。"""
    ids = ",".join(sorted(set(CG_IDS.values())))
    url = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=" + ids +
           "&price_change_percentage=24h&per_page=250&page=1")
    try:
        return {row["id"]: row for row in _get_json(url, timeout=15)}
    except Exception:
        return None


def _coinpaprika_prl():
    try:
        return _get_json(PRL_URL, timeout=10)
    except Exception:
        return None


def _system_proxies():
    """读取环境变量或 Windows Internet 设置中的代理（GUI 程序常常需要）。"""
    proxies = {}
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        val = os.environ.get(key)
        if val:
            proxies["http"] = val
            proxies["https"] = val
            return proxies
    if sys.platform == "win32":
        try:
            import winreg
            path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
                enable = winreg.QueryValueEx(k, "ProxyEnable")[0]
                server = winreg.QueryValueEx(k, "ProxyServer")[0]
            if enable and server:
                if "=" in server:
                    for part in server.split(";"):
                        if "=" in part:
                            proto, addr = part.split("=", 1)
                            proxies[proto.strip().lower()] = f"http://{addr.strip()}"
                else:
                    proxies = {"http": f"http://{server}", "https": f"http://{server}"}
        except Exception:
            pass
    return proxies


_OPENER = None


def _opener():
    global _OPENER
    if _OPENER is None:
        proxies = _system_proxies()
        _OPENER = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
    return _OPENER

# 离线兜底（2026-11-02 抓取快照，仅在完全无网络时使用）
FALLBACK = {
    "btc_usd": 77919.0,
    "coins": {
        "PRL": {"name": "Pearl", "algo": "Pearl", "nethash": 8.0858e19, "block_time": 179.0,
                "block_reward": 2201.8, "price_usd": 1.35, "difficulty": 51420717.0},
        "ETC": {"name": "EthereumClassic", "algo": "Etchash", "nethash": 1.8768e14, "block_time": 13.59,
                "block_reward": 1.59, "price_usd": 7.02, "difficulty": 2.5508e15},
        "RVN": {"name": "Ravencoin", "algo": "KawPow", "nethash": 4.9887e11, "block_time": 60.0,
                "block_reward": 1250.0, "price_usd": 0.001334, "difficulty": 6969.0},
        "ERG": {"name": "Ergo", "algo": "Autolykos", "nethash": 5.023e11, "block_time": 125.0,
                "block_reward": 3.0, "price_usd": 0.2832, "difficulty": 6.2787e13},
        "IRON": {"name": "IronFish", "algo": "FishHash", "nethash": 6.7429e10, "block_time": 62.0,
                 "block_reward": 17.25, "price_usd": 0.0091, "difficulty": 4.1806e12},
        "NEXA": {"name": "Nexa", "algo": "NexaPow", "nethash": 1.7393e12, "block_time": 142.0,
                 "block_reward": 5000000.0, "price_usd": 0.0000011, "difficulty": 57504.0},
        "XNA": {"name": "Neurai", "algo": "KawPow", "nethash": 3.3814e10, "block_time": 61.0,
                "block_reward": 3000.0, "price_usd": 0.00003, "difficulty": 480.0},
    },
}


@dataclass
class CoinMarket:
    tag: str
    name: str
    algo: str
    nethash: float          # H/s
    block_time: float       # s
    block_reward: float
    price_usd: float
    difficulty: float = 0.0
    change_24h: object = None      # 24h 涨跌 %，None 表示无数据
    volume_24h: float = 0.0        # 24h 成交额（USD）
    market_cap: float = 0.0

    @property
    def emission_day(self):
        return 86400.0 / max(self.block_time, 1e-6) * self.block_reward

    def daily_coin(self, hashrate):
        if self.nethash <= 0:
            return 0.0
        return hashrate / self.nethash * self.emission_day


@dataclass
class MarketData:
    coins: dict = field(default_factory=dict)      # tag -> CoinMarket
    btc_usd: float = 0.0
    updated: float = 0.0
    source: str = "离线快照"
    error: str = ""
    prl_from_cg: bool = False      # 本次 PRL 价是否来自 CoinGecko（否则不覆盖已有价）

    def get(self, tag):
        return self.coins.get(tag)


def _get_json(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with _opener().open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def _btc_price():
    for url in BTC_SOURCES:
        try:
            data = _get_json(url, timeout=12)
            if "bitcoin" in data:
                return float(data["bitcoin"]["usd"])
            if "quotes" in data:
                return float(data["quotes"]["USD"]["price"])
            if "price" in data:
                return float(data["price"])
        except Exception:
            continue
    return None


def _cache_path(app_dir):
    return os.path.join(app_dir, "data", "market_cache.json")


def load_cache(app_dir):
    p = _cache_path(app_dir)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cache(app_dir, payload):
    p = _cache_path(app_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception:
        pass


def _from_payload(payload):
    md = MarketData(btc_usd=payload.get("btc_usd", 0), updated=payload.get("updated", 0),
                    source=payload.get("source", "缓存"))
    for tag, c in payload.get("coins", {}).items():
        md.coins[tag] = CoinMarket(tag, c.get("name", tag), c.get("algo", ""), c.get("nethash", 0),
                                   c.get("block_time", 1), c.get("block_reward", 0),
                                   c.get("price_usd", 0), c.get("difficulty", 0),
                                   c.get("change_24h"), c.get("volume_24h", 0),
                                   c.get("market_cap", 0))
    return md


def fallback_market():
    md = MarketData(btc_usd=FALLBACK["btc_usd"], updated=time.time(), source="内置快照")
    for tag, c in FALLBACK["coins"].items():
        md.coins[tag] = CoinMarket(tag, c["name"], c["algo"], c["nethash"], c["block_time"],
                                   c["block_reward"], c["price_usd"], c["difficulty"])
    return md


def fetch_market(wanted_tags):
    """拉取实时行情（多个源并发，整体受超时保护）。"""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as ex:
        f_btc = ex.submit(_btc_price)
        f_wt = ex.submit(lambda: _get_json(WT_URL, timeout=18))
        f_cg = ex.submit(_coingecko_markets)
        f_prl = ex.submit(_coinpaprika_prl)

        try:
            btc = f_btc.result(timeout=25)
        except Exception:
            btc = None
        try:
            wm = f_wt.result(timeout=25).get("coins", {})
        except Exception as exc:
            raise RuntimeError(f"网络数据获取失败: {exc}")
        try:
            cg = f_cg.result(timeout=20)
        except Exception:
            cg = None
        try:
            prl = f_prl.result(timeout=20)
        except Exception:
            prl = None

    md = MarketData(updated=time.time(), source="whattomine")
    md.btc_usd = btc or FALLBACK["btc_usd"]

    wanted = set(wanted_tags)
    for row in wm.values():
        tag = (row.get("tag") or "").strip().upper()
        if tag not in wanted:
            continue
        price = float(row.get("exchange_rate") or 0) * md.btc_usd
        prev = float(row.get("exchange_rate24") or 0) * md.btc_usd
        change = ((price / prev - 1) * 100) if prev > 0 else None
        md.coins[tag] = CoinMarket(
            tag=tag, name=row.get("name", tag), algo=row.get("algorithm", ""),
            nethash=float(row.get("nethash") or 0), block_time=float(row.get("block_time") or 1),
            block_reward=float(row.get("block_reward") or 0), price_usd=price,
            difficulty=float(row.get("difficulty") or 0), change_24h=change)

    # 现货价校正（低价币的 BTC 折算会被精度截断）
    cg_hit = _apply_coingecko(md, cg)
    if cg_hit:
        md.source = "whattomine + coingecko"
    md.prl_from_cg = bool(cg and CG_IDS["PRL"] in cg)

    # 只有在完全拿不到 CoinGecko 的 PRL 价时才退回 CoinPaprika
    if "PRL" in md.coins and not md.prl_from_cg:
        try:
            live = float(prl["quotes"]["USD"]["price"])
            if live > 0:
                md.coins["PRL"].price_usd = live
                ch = prl.get("quotes", {}).get("USD", {}).get("percent_change_24h")
                if ch is not None:
                    md.coins["PRL"].change_24h = float(ch)
                md.source = "whattomine + coinpaprika"
        except Exception:
            pass

    if not md.coins:
        raise RuntimeError("行情源未返回目标币种")
    return md



def fetch_prices():
    """轻量价格轮询：只取现货价与 24h 涨跌，用于 3 秒级刷新。"""
    out = {}
    data = _coingecko_prices()
    if data:
        for tag, cid in CG_IDS.items():
            row = data.get(cid)
            if not row:
                continue
            try:
                out[tag] = (float(row["usd"]), row.get("usd_24h_change"))
            except (KeyError, TypeError, ValueError):
                continue
    if "PRL" not in out:
        p = _coinpaprika_prl()
        try:
            q = p["quotes"]["USD"]
            out["PRL"] = (float(q["price"]), q.get("percent_change_24h"))
        except Exception:
            pass
    if not out:
        raise RuntimeError("价格源无响应")
    return out


def snapshot_payload(md):
    return {
        "btc_usd": md.btc_usd,
        "updated": md.updated,
        "source": md.source,
        "coins": {t: {"name": c.name, "algo": c.algo, "nethash": c.nethash,
                      "block_time": c.block_time, "block_reward": c.block_reward,
                      "price_usd": c.price_usd, "difficulty": c.difficulty,
                      "change_24h": c.change_24h, "volume_24h": c.volume_24h,
                      "market_cap": c.market_cap}
                  for t, c in md.coins.items()},
    }
