"""收益计算：币本位产出 / 毛收益 / 电费 / 净收益，支持多时间单位与货币切换。"""

from dataclasses import dataclass

UNIT_HOURS = {
    "小时": 1.0,
    "天": 24.0,
    "周": 168.0,
    "月": 720.0,
    "年": 8760.0,
}
UNIT_ORDER = ["小时", "天", "周", "月", "年"]


@dataclass
class Profit:
    symbol: str
    hashrate: float          # H/s
    coin_day: float          # 币/天
    gross_usd_day: float
    power_w: float
    kwh_day: float
    elec_cny_day: float
    net_cny_day: float

    def gross(self, hours, cny_per_usd=7.1, currency="CNY"):
        v = self.gross_usd_day * hours / 24.0 * cny_per_usd
        return v if currency == "CNY" else self.gross_usd_day * hours / 24.0

    def net(self, hours, currency="CNY"):
        v = self.net_cny_day * hours / 24.0
        return v if currency == "CNY" else v / 7.1

    def coin(self, hours):
        return self.coin_day * hours / 24.0


def compute(coin, gpu_hash, coin_market, elec_cny_kwh, power_w, usd_cny=7.1, pool_fee=0.01):
    """单卡单币收益。gpu_hash 为 H/s。"""
    coin_day = coin_market.daily_coin(gpu_hash) * (1 - pool_fee)
    gross_usd = coin_day * coin_market.price_usd
    kwh = power_w / 1000.0 * 24.0
    elec = kwh * elec_cny_kwh
    net = gross_usd * usd_cny - elec
    return Profit(coin.symbol, gpu_hash, coin_day, gross_usd, power_w, kwh, elec, net)


def fmt_money(v, currency="CNY"):
    sign = "-" if v < 0 else ""
    v = abs(v)
    if currency == "CNY":
        if v >= 10000:
            return f"{sign}¥{v/1000:,.1f}k"
        return f"{sign}¥{v:,.2f}"
    if v >= 10000:
        return f"{sign}${v/1000:,.1f}k"
    return f"{sign}${v:,.2f}"


def fmt_price(price):
    """价格显示：按量级自动取舍，避免出现 2.99e-05 这种科学计数法。"""
    if not price or price <= 0:
        return "—"
    if price >= 1000:
        return f"${price:,.0f}"
    if price >= 1:
        return f"${price:,.2f}"
    if price >= 0.01:
        return f"${price:.4f}"
    if price >= 0.0001:
        return f"${price:.6f}"
    if price >= 0.000001:
        return f"${price:.8f}".rstrip("0").rstrip(".")
    return f"${price:.10f}".rstrip("0").rstrip(".")


def fmt_usd(v):
    if v >= 1_000_000:
        return f"${v/1_000_000:,.2f}M"
    if v >= 1000:
        return f"${v/1000:,.1f}k"
    return f"${v:,.0f}"


def fmt_num(v, digits=4):
    if v == 0:
        return "0"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v) >= 1:
        return f"{v:,.{min(digits, 2)}f}"
    return f"{v:.{digits}f}".rstrip("0").rstrip(".") or "0"


def fmt_power(w):
    return f"{w:,.0f} W"
