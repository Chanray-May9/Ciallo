"""应用上下文：配置、行情、显卡、收益计算的统一入口。"""

import time

from PySide6.QtCore import QObject, Signal, QThread

from . import gpu as gpu_mod
from . import market as market_mod
from . import profit as profit_mod
from . import store
from .catalog import COINS, COIN_BY_SYMBOL, GPU_BY_KEY, coin_from_custom


class _FetchThread(QThread):
    done = Signal(object, str)

    def __init__(self, tags, parent=None):
        super().__init__(parent)
        self.tags = tags

    def run(self):
        try:
            md = market_mod.fetch_market(self.tags)
            self.done.emit(md, "")
        except Exception as exc:      # 网络异常由上层降级处理
            self.done.emit(None, str(exc))


class _PriceThread(QThread):
    done = Signal(object, str)

    def run(self):
        try:
            self.done.emit(market_mod.fetch_prices(), "")
        except Exception as exc:
            self.done.emit(None, str(exc))


class AppContext(QObject):
    marketChanged = Signal()
    displayChanged = Signal()
    configChanged = Signal()
    coinsChanged = Signal()

    def __init__(self, app_dir, parent=None):
        super().__init__(parent)
        self.app_dir = app_dir
        self.cfg = store.load(app_dir)
        self.gpu = gpu_mod.detect()
        self._thread = None
        self.loading = False
        self.last_error = ""
        self.last_update = 0.0

        cached = market_mod.load_cache(app_dir)
        self.market = market_mod._from_payload(cached) if cached else market_mod.fallback_market()
        if cached:
            self.last_update = cached.get("updated", 0)
        self.gpu_key = self.cfg.gpu_key or self.gpu.key or "rtx4070lap"
        # 曲线基准切换（旧版按推荐币采样）时清空历史，避免出现假跳变
        if getattr(self.cfg, "history_base", "") != "PRL4":
            self.cfg.history = []
            self.cfg.history_base = "PRL4"
            store.save(app_dir, self.cfg)
        self._price_thread = None
        self._price_busy = False
        self._price_cooldown = 0.0
        self._prl_lock = False        # 一旦拿到 CoinGecko 的 PRL 价就锁定，避免两个数据源来回跳
        self._prl_px = 0.0
        self._perf_saved = 0.0
        self._hist_saved = 0.0

    # ---------------------------------------------------------------- 显卡
    @property
    def gpu_model(self):
        return GPU_BY_KEY.get(self.gpu_key) or GPU_BY_KEY["rtx4070lap"]

    @property
    def perf(self):
        try:
            return max(0, min(100, int(self.cfg.perf_pct))) / 100.0
        except (TypeError, ValueError):
            return 1.0

    def power_w(self):
        base = (self.cfg.power_limit if self.cfg.power_limit and self.cfg.power_limit > 10
                else gpu_mod.default_power(self.gpu_key, self.gpu.power_limit))
        return float(base) * self.perf

    def hashrate(self, coin, scale=None):
        """算力 = 参考算力（或校准值）× 性能占用百分比；scale 可强制指定比例。"""
        factor = self.perf if scale is None else scale
        if coin.symbol in self.cfg.hash_overrides:
            try:
                base = float(self.cfg.hash_overrides[coin.symbol])
            except (TypeError, ValueError):
                base = float(self.gpu_model.perf.get(coin.algo_key, 0.0))
        elif coin.custom:
            base = float(coin.data.get("hashrate") or 0)
        else:
            base = float(self.gpu_model.perf.get(coin.algo_key, 0.0))
        return base * factor

    # ---------------------------------------------------------------- 币种
    def coins(self):
        out = list(COINS)
        for d in self.cfg.custom_coins:
            try:
                out.append(coin_from_custom(d))
            except Exception:
                continue
        return out

    def coin(self, symbol):
        for c in self.coins():
            if c.symbol == symbol:
                return c
        return self.coins()[0]

    def upsert_custom(self, data):
        sym = (data.get("symbol") or "").upper()
        if not sym:
            return
        data["symbol"] = sym
        rest = [d for d in self.cfg.custom_coins if (d.get("symbol") or "").upper() != sym]
        rest.append(data)
        self.cfg.custom_coins = rest
        self.save()
        self.coinsChanged.emit()
        self.displayChanged.emit()

    def remove_custom(self, symbol):
        self.cfg.custom_coins = [d for d in self.cfg.custom_coins
                                 if (d.get("symbol") or "").upper() != symbol.upper()]
        self.save()
        self.coinsChanged.emit()
        self.displayChanged.emit()

    # ---------------------------------------------------------------- 收益
    def _market_for(self, coin):
        if coin.custom:
            d = coin.data
            return market_mod.CoinMarket(
                tag=coin.symbol, name=coin.name, algo=coin.algo,
                nethash=float(d.get("nethash") or 0),
                block_time=float(d.get("block_time") or 0) or 1.0,
                block_reward=float(d.get("block_reward") or 0),
                price_usd=float(d.get("price_usd") or 0),
                difficulty=0.0, change_24h=None)
        return self.market.get(coin.wm_tag)

    def profit(self, coin, scale=None):
        cm = self._market_for(coin)
        hr = self.hashrate(coin, scale)
        if not cm or cm.nethash <= 0:
            return None
        return profit_mod.compute(coin, hr, cm, self.cfg.electricity, self.power_w(),
                                  self.cfg.usd_cny)

    def profit_base(self, coin):
        """满血（100%）口径，用于排行榜与收益曲线，保证基准不随滑块变化。"""
        return self.profit(coin, scale=1.0)

    def profits(self):
        out = []
        for c in self.coins():
            p = self.profit(c)
            if p:
                out.append((c, p))
        return out

    def revenue_cny(self, p):
        if p is None:
            return 0.0
        if self.cfg.use_electricity:
            return p.net_cny_day
        return p.gross_usd_day * self.cfg.usd_cny

    def rev_label(self):
        return "净收益" if self.cfg.use_electricity else "收益"

    def liquidity(self, coin):
        """按「你的日收益 / 该币 24h 成交额」判断出货难度。"""
        cm = self._market_for(coin)
        if not cm or cm.volume_24h <= 0:
            return "unknown"
        p = self.profit(coin)
        daily_usd = (self.revenue_cny(p) / max(self.cfg.usd_cny, 0.01)) if p else 0.0
        vol = cm.volume_24h
        if vol >= 3_000_000 and daily_usd / vol < 0.001:
            return "high"
        if vol >= 50_000 and daily_usd / vol < 0.01:
            return "mid"
        return "low"

    def liquidity_label(self, coin):
        return {"high": "流动性好", "mid": "流动性一般",
                "low": "流动性差", "unknown": "无成交数据"}[self.liquidity(coin)]

    def best(self):
        """推荐位固定给主推币 PRL；没有 PRL 数据时才退回收益最高的币。"""
        prl = self.coin("PRL")
        p = self.profit(prl)
        if p is not None:
            return (prl, p)
        rows = self.profits()
        return max(rows, key=lambda r: self.revenue_cny(r[1])) if rows else (None, None)

    # ---------------------------------------------------------------- 单位
    def unit_hours(self):
        return profit_mod.UNIT_HOURS.get(self.cfg.unit, 24.0)

    def money(self, cny_value, hours_factor=None):
        hours = self.unit_hours() if hours_factor is None else hours_factor
        v = cny_value * hours / 24.0
        if self.cfg.currency == "USD":
            v /= max(self.cfg.usd_cny, 0.01)
            return profit_mod.fmt_money(v, "USD")
        return profit_mod.fmt_money(v, "CNY")

    # ---------------------------------------------------------------- 行情
    def refresh_async(self):
        if self.loading:
            return False
        self.loading = True
        self._thread = _FetchThread([c.wm_tag for c in COINS], self)
        self._thread.done.connect(self._on_fetched)
        self._thread.start()
        return True

    def refresh_prices_async(self):
        """3 秒级价格刷新；遇到限流自动退避 60 秒。"""
        if self._price_busy or time.time() < self._price_cooldown:
            return False
        self._price_busy = True
        self._price_thread = _PriceThread(self)
        self._price_thread.done.connect(self._on_prices)
        self._price_thread.start()
        return True

    def _on_prices(self, data, err):
        self._price_busy = False
        if err or not data:
            self._price_cooldown = time.time() + 60
            return
        changed = False
        for tag, (price, change) in data.items():
            cm = self.market.coins.get(tag)
            if not cm or price <= 0:
                continue
            if tag == "PRL":
                self._prl_lock = True
                self._prl_px = float(price)
            if abs(cm.price_usd - price) > 1e-12:
                changed = True
            cm.price_usd = float(price)
            if change is not None:
                cm.change_24h = float(change)
        self.last_update = time.time()
        if changed:
            self.marketChanged.emit()

    def _on_fetched(self, md, err):
        self.loading = False
        if md is not None:
            old = self.market.coins.get("PRL")
            old_px = old.price_usd if old else 0.0
            # 已有价格时，只有 CoinGecko 的新数据才允许覆盖，避免两个源来回跳
            if old_px > 0 and not md.prl_from_cg and not self._prl_lock:
                md.coins["PRL"].price_usd = old_px
            elif self._prl_lock and self._prl_px > 0:
                md.coins["PRL"].price_usd = self._prl_px
            self.market = md
            self.last_update = md.updated
            self.last_error = ""
            market_mod.save_cache(self.app_dir, market_mod.snapshot_payload(md))
        else:
            self.last_error = err
        self._push_history()
        self.marketChanged.emit()

    def sample_history(self):
        """供定时器调用：稳定地按时间采样，不依赖行情事件。"""
        self._push_history()

    def _push_history(self):
        # 每秒采样一次；曲线用满血口径，不随性能滑块变化
        p = self.profit_base(self.coin("PRL"))
        if p is None:
            return
        now = int(time.time())
        hist = list(self.cfg.history)
        if hist and now <= int(hist[-1][0]):
            return
        hist.append([now, round(self.revenue_cny(p), 4)])
        self.cfg.history = hist[-7200:]
        # 每 15 秒才落盘一次，避免每秒写文件
        if now - self._hist_saved >= 15:
            self._hist_saved = now
            store.save(self.app_dir, self.cfg)

    def save(self):
        store.save(self.app_dir, self.cfg)
        self.configChanged.emit()

    def set_display(self, unit=None, currency=None):
        if unit:
            self.cfg.unit = unit
        if currency:
            self.cfg.currency = currency
        store.save(self.app_dir, self.cfg)
        self.displayChanged.emit()

    def set_perf(self, pct):
        self.cfg.perf_pct = max(0, min(100, int(pct)))
        now = time.monotonic()
        if now - self._perf_saved > 0.4:      # 拖动时不必每个像素都写盘
            store.save(self.app_dir, self.cfg)
            self._perf_saved = now
        self.displayChanged.emit()

    def status_line(self):
        if self.loading:
            return "正在同步行情…"
        ts = time.strftime("%H:%M:%S", time.localtime(self.last_update)) if self.last_update else "--:--:--"
        if self.last_error:
            return f"离线数据 · 上次成功 {ts}"
        return f"{self.market.source} · 更新于 {ts}"

