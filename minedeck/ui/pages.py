"""四个主页面：概览 / 币种 / 开挖 / 设置，以及自定义币种对话框。"""

import os
import re
import time

from PySide6.QtCore import Qt, Signal, QTimer, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                               QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
                               QSpinBox, QVBoxLayout, QWidget)

from .. import miners as miners_mod
from .. import profit as profit_mod
from ..catalog import (COIN_MINER, COINS, MINERS, REFERENCES, UNIT_DIV, build_args, fmt_hash,
                       miners_for, pools_for)
from ..theme import C
from .widgets import (BTN_W, COL_CHG, COL_COIN, COL_HASH, COL_NET, Card, Chip, CoinRow,
                      Divider, KV, ModernSelect, PerfSlider, Segmented, Sparkline, h1, h2, label)

WALLET_HINT = {
    "PRL": "PRL 收款地址（官方钱包 prl1… 或交易所充值地址）",
    "ETC": "0x 开头的 ETC 地址",
    "RVN": "R 开头的 RVN 地址",
    "ERG": "9 开头的 Ergo 地址",
    "IRON": "iron… 开头的 Iron Fish 地址",
    "NEXA": "nexa: 开头的地址",
    "XNA": "N 开头的 Neurai 地址",
}

# 币种 -> (网络名称, 地址格式说明, 选错链的后果提示)
WALLET_NET = {
    "PRL": ("Pearl 主网", "prl1… 开头（bech32）",
            "交易所提现时网络请选 PRL / Pearl，不要选 ERC20、BEP20 等"),
    "ETC": ("Ethereum Classic 主网", "0x… 开头 42 位",
            "选 ETC 主网，不要选 ETH / ERC20，两个链地址长得像但不通用"),
    "RVN": ("Ravencoin 主网", "R… 开头",
            "选 RVN 主网，不要选 BTC 或其它 UTXO 链"),
    "ERG": ("Ergo 主网", "9… 开头",
            "选 ERG 主网，Ergo 地址与 BTC 格式不同，勿混用"),
    "IRON": ("Iron Fish 主网", "iron… 开头",
             "选 IRON 主网，Iron Fish 地址不能用其它链的地址"),
    "NEXA": ("Nexa 主网", "nexa:… 开头",
             "选 NEXA 主网，注意小数位精度"),
    "XNA": ("Neurai 主网", "N… 开头",
            "选 XNA 主网，Neurai 与 RVN 同为 KawPow 但地址不通用"),
}


def field(title, widget, hint=""):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    lay.addWidget(label(title, "label"))
    lay.addWidget(widget)
    if hint:
        lay.addWidget(label(hint, "tiny"))
    return w


def page_header(title, sub, right_widgets=()):
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(12)
    left = QVBoxLayout()
    left.setSpacing(3)
    left.addWidget(h1(title))
    left.addWidget(label(sub, "muted"))
    lay.addLayout(left)
    lay.addStretch(1)
    for w in right_widgets:
        lay.addWidget(w, 0, Qt.AlignVCenter)
    return box


# ====================================================================== 自定义币种
class CustomCoinDialog(QDialog):
    def __init__(self, ctx, existing=None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.existing = existing or {}
        self.setWindowTitle("自定义币种")
        self.setMinimumWidth(620)
        self.setStyleSheet(f"QDialog{{background:{C.SURFACE};}}")

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)
        root.addWidget(h2("自定义币种"))
        root.addWidget(label("填你自己币种的网络参数，MineDeck 会用同一套公式算收益并生成开挖命令", "tiny"))

        d = self.existing
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        self.symbol = QLineEdit(d.get("symbol", ""))
        self.symbol.setPlaceholderText("如 FOO")
        self.name = QLineEdit(d.get("name", ""))
        self.name.setPlaceholderText("如 FooCoin")
        self.algo = QLineEdit(d.get("algo", ""))
        self.algo.setPlaceholderText("算法显示名，如 KawPow")
        self.unit = ModernSelect()
        self.unit.addItems(["H/s", "KH/s", "MH/s", "GH/s", "TH/s"])
        self.unit.setCurrentText(d.get("unit", "MH/s"))

        self.hashrate = QLineEdit(self._num(d.get("hashrate"), d.get("unit", "MH/s")))
        self.hashrate.setPlaceholderText("我的算力（按左边单位）")
        self.nethash = QLineEdit(self._num(d.get("nethash"), d.get("unit", "MH/s")))
        self.nethash.setPlaceholderText("全网算力（按左边单位）")
        self.block_time = QLineEdit(str(d.get("block_time", 60)))
        self.block_reward = QLineEdit(str(d.get("block_reward", 100)))
        self.price = QLineEdit(str(d.get("price_usd", 0.001)))
        self.pool_host = QLineEdit(d.get("pool_host", ""))
        self.pool_host.setPlaceholderText("矿池地址，如 pool.example.com")
        self.pool_port = QLineEdit(str(d.get("pool_port", "")))
        self.pool_port.setPlaceholderText("端口")
        self.miner = ModernSelect()
        self.miner.addItems(["lolminer", "srbminer", "lpminer"])
        self.miner.setCurrentText(d.get("miner", "lolminer"))
        self.algo_arg = QLineEdit(d.get("algo_arg", ""))
        self.algo_arg.setPlaceholderText("内核算法参数，如 KAWPOW / pearlhash")
        self.network = QLineEdit(d.get("network", ""))
        self.network.setPlaceholderText("收款网络，如 Pearl 主网 / ETC 主网")

        grid.addWidget(field("符号", self.symbol), 0, 0)
        grid.addWidget(field("名称", self.name), 0, 1)
        grid.addWidget(field("算力单位", self.unit), 1, 0)
        grid.addWidget(field("我的算力", self.hashrate), 1, 1)
        grid.addWidget(field("全网算力", self.nethash), 2, 0)
        grid.addWidget(field("区块时间（秒）", self.block_time), 2, 1)
        grid.addWidget(field("区块奖励（币）", self.block_reward), 3, 0)
        grid.addWidget(field("单价（USD）", self.price), 3, 1)
        grid.addWidget(field("矿池地址", self.pool_host), 4, 0)
        grid.addWidget(field("矿池端口", self.pool_port), 4, 1)
        grid.addWidget(field("内核", self.miner), 5, 0)
        grid.addWidget(field("算法参数", self.algo_arg), 5, 1)
        grid.addWidget(field("收款网络", self.network), 6, 0)
        root.addLayout(grid)

        self.err = label("", "tiny")
        self.err.setStyleSheet(f"color:{C.RED};")
        root.addWidget(self.err)

        row = QHBoxLayout()
        if self.existing:
            bdel = QPushButton("删除")
            bdel.setObjectName("danger")
            bdel.setCursor(Qt.PointingHandCursor)
            bdel.clicked.connect(self._delete)
            row.addWidget(bdel)
        row.addStretch(1)
        bcancel = QPushButton("取消")
        bcancel.setObjectName("ghost")
        bcancel.setCursor(Qt.PointingHandCursor)
        bcancel.clicked.connect(self.reject)
        bsave = QPushButton("保存币种")
        bsave.setObjectName("primary")
        bsave.setCursor(Qt.PointingHandCursor)
        bsave.clicked.connect(self._save)
        row.addWidget(bcancel)
        row.addWidget(bsave)
        root.addLayout(row)

    @staticmethod
    def _num(v, unit):
        if not v:
            return ""
        try:
            return f"{float(v) / UNIT_DIV.get(unit, 1.0):.6g}"
        except (TypeError, ValueError):
            return ""

    def _save(self):
        sym = self.symbol.text().strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{2,10}", sym):
            self.err.setText("符号需要 2-10 位字母或数字")
            return
        try:
            unit = self.unit.currentText()
            mult = UNIT_DIV[unit]
            hashrate = float(self.hashrate.text() or 0) * mult
            nethash = float(self.nethash.text() or 0) * mult
            bt = float(self.block_time.text() or 0)
            reward = float(self.block_reward.text() or 0)
            price = float(self.price.text() or 0)
            port = int(self.pool_port.text() or 0)
        except ValueError:
            self.err.setText("数字格式不正确，请检查算力 / 区块 / 价格")
            return
        if hashrate <= 0 or nethash <= 0 or bt <= 0 or reward <= 0:
            self.err.setText("算力、全网算力、区块时间、区块奖励都必须大于 0")
            return

        data = dict(self.existing)
        data.update({
            "symbol": sym,
            "name": self.name.text().strip() or sym,
            "algo": self.algo.text().strip() or "自定义算法",
            "unit": unit,
            "hashrate": hashrate,
            "nethash": nethash,
            "block_time": bt,
            "block_reward": reward,
            "price_usd": price,
            "pool_host": self.pool_host.text().strip(),
            "pool_port": port,
            "miner": self.miner.currentText(),
            "algo_arg": self.algo_arg.text().strip(),
            "network": self.network.text().strip(),
            "color": self.existing.get("color") or "#7C3AED",
        })
        self.ctx.upsert_custom(data)
        self.accept()

    def _delete(self):
        self.ctx.remove_custom(self.existing.get("symbol", ""))
        self.accept()


# ====================================================================== 概览
class DashboardPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 20)
        root.setSpacing(14)

        root.addWidget(page_header("概览", "主推 PRL，全部币种收益实时对比"))

        row = QHBoxLayout()
        row.setSpacing(14)

        c1 = Card()
        c1.body.addWidget(label("当前显卡", "label"))
        self.gpu_name = QLabel("—")
        self.gpu_name.setObjectName("value")
        self.gpu_name.setWordWrap(True)
        c1.body.addWidget(self.gpu_name)
        self.gpu_meta = label("", "tiny")
        c1.body.addWidget(self.gpu_meta)
        self.gpu_hash = label("", "mono")
        c1.body.addWidget(self.gpu_hash)
        c1.body.addStretch(1)
        self.perf = PerfSlider(ctx.cfg.perf_pct)
        self.perf.changed.connect(self.ctx.set_perf)
        c1.body.addWidget(self.perf)
        self.perf_hint = label("", "tiny")
        c1.body.addWidget(self.perf_hint)

        c2 = Card()
        top2 = QHBoxLayout()
        top2.addWidget(label("推荐币种", "label"))
        top2.addStretch(1)
        self.liq_chip = Chip("—")
        top2.addWidget(self.liq_chip)
        c2.body.addLayout(top2)
        self.best_sym = QLabel("—")
        self.best_sym.setObjectName("value")
        c2.body.addWidget(self.best_sym)
        self.best_sub = label("", "tiny")
        self.best_sub.setWordWrap(True)
        c2.body.addWidget(self.best_sub)
        c2.body.addStretch(1)
        self.best_extra = label("", "mono")
        c2.body.addWidget(self.best_extra)

        c3 = Card()
        top3 = QHBoxLayout()
        top3.addWidget(label("当前收益", "label"))
        top3.addStretch(1)
        self.rev_chip = Chip("¥ / 天", C.TEXT_2, "#F1F2F6")
        top3.addWidget(self.rev_chip)
        c3.body.addLayout(top3)
        self.rev_value = QLabel("—")
        self.rev_value.setObjectName("big")
        self.rev_value.setStyleSheet(f"color:{C.GREEN};")
        c3.body.addWidget(self.rev_value)
        self.rev_sub = label("", "tiny")
        c3.body.addWidget(self.rev_sub)
        c3.body.addStretch(1)
        self.rev_gross = label("", "mono")
        c3.body.addWidget(self.rev_gross)

        for c in (c1, c2, c3):
            row.addWidget(c, 1)
        root.addLayout(row)

        row2 = QHBoxLayout()
        row2.setSpacing(14)

        chart_card = Card()
        head = QHBoxLayout()
        head.addWidget(h2("PRL 收益曲线"))
        head.addWidget(label("固定基准 · 时间轴从右往左生长", "tiny"))
        head.addStretch(1)
        self.chart_chip = Chip("—")
        head.addWidget(self.chart_chip)
        chart_card.body.addLayout(head)
        self.chart = Sparkline()
        chart_card.body.addWidget(self.chart, 1)
        row2.addWidget(chart_card, 3)

        topcard = Card()
        topcard.body.addWidget(h2("币种收益排行"))
        topcard.body.addStretch(1)
        self.top_holder = QVBoxLayout()
        self.top_holder.setSpacing(0)
        topcard.body.addLayout(self.top_holder)
        topcard.body.addStretch(1)
        self.top_rows = {}
        self._top_order = []
        self._top_symbols = []
        self._build_top_rows()
        self.top_footer = label("", "tiny")
        topcard.body.addWidget(self.top_footer)
        row2.addWidget(topcard, 2)
        root.addLayout(row2, 1)

        root.addWidget(label("口径：毛收益（不扣电费），可在设置中开启电费扣除 · "
                             "算力为公开资料参考值，可在设置里按实测校准", "tiny"))

    def _build_top_rows(self):
        while self.top_holder.count():
            item = self.top_holder.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.top_rows = {}
        self._top_order = []
        self._top_symbols = []
        for c in self.ctx.coins():
            item = QWidget()
            lay = QHBoxLayout(item)
            lay.setContentsMargins(0, 7, 0, 7)
            lay.setSpacing(8)
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background:{c.color};border-radius:4px;")
            lay.addWidget(dot)
            sym = QLabel(c.symbol)
            sym.setStyleSheet("font-weight:700;font-size:12px;")
            sym.setFixedWidth(46)
            lay.addWidget(sym)
            lay.addWidget(label(c.name_cn, "tiny"))
            lay.addStretch(1)
            value = QLabel("—")
            value.setStyleSheet(f"font-family:{C.MONO};font-size:13px;font-weight:700;"
                                f"color:{C.GREEN};")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lay.addWidget(value)
            self.top_holder.addWidget(item)
            self.top_rows[c.symbol] = (item, value)
            self._top_order.append(c.symbol)
            self._top_symbols.append(c.symbol)

    def refresh(self):
        ctx = self.ctx
        g = ctx.gpu_model
        self.perf.set_value(ctx.cfg.perf_pct)
        self.gpu_name.setText(g.name)
        self.gpu_meta.setText(f"{g.vram} GB · 参考功耗 {g.tdp} W · 当前 {ctx.power_w():.0f} W")
        self.gpu_meta.setToolTip(f"检测到：{ctx.gpu.name}（{ctx.gpu.source}）")
        prl = ctx.coin("PRL")
        self.gpu_hash.setText(f"PRL 算力 {fmt_hash(ctx.hashrate(prl))}")
        if ctx.cfg.perf_pct >= 100:
            self.perf_hint.setText("100% = 满血跑；调低可降温降噪，收益按比例下降")
        elif ctx.cfg.perf_pct <= 0:
            self.perf_hint.setText("0% = 不挖矿")
        else:
            self.perf_hint.setText(f"按 {ctx.cfg.perf_pct}% 性能估算，收益与功耗同比缩放")

        coin, p = ctx.best()
        if coin and p:
            cm = ctx._market_for(coin)
            self.best_sym.setText(f"{coin.symbol} · {coin.name_cn}")
            self.best_sub.setText(coin.note or coin.algo)
            self.liq_chip.set_state("主推", C.ACCENT, C.ACCENT_SOFT)
            vol = profit_mod.fmt_usd(cm.volume_24h) if cm and cm.volume_24h > 0 else "—"
            self.best_extra.setText(f"价格 ${cm.price_usd:,.6g} · 24h 成交额 {vol}" if cm else "")
            rev = ctx.revenue_cny(p)
            self.rev_value.setText(ctx.money(rev))
            self.rev_value.setStyleSheet(f"color:{C.GREEN if rev >= 0 else C.RED};")
            self.rev_chip.set_state(f"{'¥' if ctx.cfg.currency == 'CNY' else '$'} / {ctx.cfg.unit}",
                                    C.TEXT_2, "#F1F2F6")
            self.rev_sub.setText(f"{coin.symbol} · 每{ctx.cfg.unit}产出 "
                                 f"{profit_mod.fmt_num(p.coin(ctx.unit_hours()), 6)} {coin.symbol}")
            gross_h = p.gross_usd_day * ctx.cfg.usd_cny / 24.0
            self.rev_gross.setText(f"毛收益 {ctx.money(p.gross_usd_day * ctx.cfg.usd_cny)}"
                                   f"  ·  每小时 {ctx.money(gross_h, 1)}")
        else:
            self.best_sym.setText("—")
            self.liq_chip.set_state("—", C.TEXT_3, "#F1F2F6")
            self.rev_value.setText("—")
            self.rev_sub.setText("把性能滑块调到 0% 以上开始估算" if ctx.cfg.perf_pct == 0 else "等待行情数据")

        hist = ctx.cfg.history[-240:]
        self.chart.set_points([(h[0], h[1]) for h in hist])
        if len(hist) >= 2:
            span_min = max(1, int((hist[-1][0] - hist[0][0]) / 60))
            delta = hist[-1][1] - hist[0][1]
            pct = (delta / hist[0][1] * 100) if hist[0][1] else 0
            self.chart_chip.set_state(f"最近 {span_min} 分钟 · {pct:+.1f}%",
                                      C.GREEN if delta >= 0 else C.RED,
                                      C.GREEN_SOFT if delta >= 0 else C.RED_SOFT)
        else:
            self.chart_chip.set_state("采集中", C.TEXT_3, "#F1F2F6")

        # 收益排行：固定按满血（100%）口径，不随性能滑块变化
        if [c.symbol for c in ctx.coins()] != self._top_symbols:
            self._build_top_rows()
        ranked = []
        for c in ctx.coins():
            p = ctx.profit_base(c)
            ranked.append((c, p, ctx.revenue_cny(p) if p else 0.0))
        ranked = [r for r in ranked if r[1] is not None]
        ranked.sort(key=lambda r: r[2], reverse=True)
        order = [c.symbol for c, _, _ in ranked]
        if order != self._top_order:
            for i, sym in enumerate(order):
                item = self.top_rows[sym][0]
                self.top_holder.insertWidget(i, item)
            self._top_order = order
        for c, p, rev in ranked:
            item, value_label = self.top_rows[c.symbol]
            value_label.setText(ctx.money(rev))
            value_label.setStyleSheet(
                f"font-family:{C.MONO};font-size:13px;font-weight:700;"
                f"color:{C.GREEN if rev >= 0 else C.RED};")
            cm = ctx._market_for(c)
            vol = profit_mod.fmt_usd(cm.volume_24h) if cm and cm.volume_24h > 0 else "—"
            item.setToolTip(f"{c.symbol} · 价格 {profit_mod.fmt_price(cm.price_usd) if cm else '—'}"
                            f" · 24h 成交额 {vol}")
        self.top_footer.setText(
            f"共 {len(ranked)} 个币种 · 按日收益从高到低 · 显示单位 "
            f"{'¥' if ctx.cfg.currency == 'CNY' else '$'}/{ctx.cfg.unit}")


# ====================================================================== 币种
class CoinsPage(QWidget):
    open_mine = Signal(str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.sort_key = "收益"
        self.query = ""
        self.rows = {}
        self._order = []
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 20)
        root.setSpacing(14)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索币种 / 算法")
        self.search.setFixedWidth(190)
        self.search.textChanged.connect(self._on_search)

        self.sort = Segmented(["收益", "产出", "涨跌"], "收益")
        self.sort.changed.connect(self._on_sort)

        btn_add = QPushButton("＋ 自定义币种")
        btn_add.setObjectName("ghost")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._add_custom)

        root.addWidget(page_header("币种收益", "选一个收益最高的币种，点右侧「开挖」即可",
                                   [self.search, self.sort, btn_add]))

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(14, 0, 12, 0)
        hl.setSpacing(10)
        first = label("币种", "tiny")
        first.setMinimumWidth(190)
        hl.addWidget(first, 3)
        for txt, w in (("我的算力", COL_HASH), ("日产出", COL_COIN),
                       ("日收益", COL_NET), ("今日", COL_CHG), ("", BTN_W), ("", BTN_W)):
            lb = label(txt, "tiny")
            lb.setFixedWidth(w)
            lb.setAlignment(Qt.AlignCenter)
            hl.addWidget(lb)
        root.addWidget(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        holder = QWidget()
        self.list_lay = QVBoxLayout(holder)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(6)
        self.scroll.setWidget(holder)
        root.addWidget(self.scroll, 1)

        root.addWidget(label("排名按当前口径的收益排序 · 数据随行情自动刷新 · "
                             "点任意一行可直接跳转到开挖页", "tiny"))

        self._rebuild()
        ctx.coinsChanged.connect(self._rebuild)

    def _rebuild(self):
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.rows = {}
        self._order = []
        for c in self.ctx.coins():
            row = CoinRow(c)
            row.action.connect(self.open_mine.emit)
            row.clicked.connect(self.open_mine.emit)
            row.edit.connect(self._edit_custom)
            self.rows[c.symbol] = row
            self.list_lay.addWidget(row)
        self.list_lay.addStretch(1)
        self.refresh()

    def _add_custom(self):
        CustomCoinDialog(self.ctx, None, self).exec()

    def _edit_custom(self, symbol):
        for d in self.ctx.cfg.custom_coins:
            if (d.get("symbol") or "").upper() == symbol.upper():
                CustomCoinDialog(self.ctx, d, self).exec()
                return

    def _on_search(self, text):
        self.query = text.strip().lower()
        self.refresh()

    def _on_sort(self, key):
        self.sort_key = key
        self.refresh()

    def refresh(self):
        ctx = self.ctx
        rows = []
        for c in ctx.coins():
            p = ctx.profit(c)
            if not p:
                continue
            cm = ctx._market_for(c)
            rows.append((c, p, cm))

        if self.query:
            rows = [r for r in rows if self.query in r[0].symbol.lower()
                    or self.query in r[0].name.lower()
                    or self.query in r[0].algo.lower()
                    or self.query in r[0].name_cn]

        if self.sort_key == "产出":
            rows.sort(key=lambda r: r[1].coin_day, reverse=True)
        elif self.sort_key == "涨跌":
            rows.sort(key=lambda r: (r[2].change_24h or -999) if r[2] else -999, reverse=True)
        else:
            rows.sort(key=lambda r: ctx.revenue_cny(r[1]), reverse=True)

        order = [c.symbol for c, _, _ in rows]
        if order != self._order:
            for i, sym in enumerate(order):
                w = self.rows.get(sym)
                if w:
                    self.list_lay.insertWidget(i, w)
            self._order = order
        for sym in order:
            w = self.rows.get(sym)
            if w:
                w.show()
        shown = {c.symbol for c, _, _ in rows}
        for sym, w in self.rows.items():
            if sym not in shown:
                w.hide()

        for c, p, cm in rows:
            w = self.rows[c.symbol]
            vol = profit_mod.fmt_usd(cm.volume_24h) if cm else "—"
            w.setToolTip(f"{c.symbol} · 24h 成交额 {vol}")
            w.update_values(
                fmt_hash(p.hashrate),
                profit_mod.fmt_num(p.coin_day, c.digits),
                ctx.money(ctx.revenue_cny(p)),
                ctx.revenue_cny(p),
                cm.change_24h if cm else None)


# ====================================================================== 开挖
class _Downloader(QThread):
    progress = Signal(int, int)
    logline = Signal(str)
    ok = Signal(str)
    fail = Signal(str)

    def __init__(self, app_dir, key, parent=None):
        super().__init__(parent)
        self.app_dir = app_dir
        self.key = key

    def run(self):
        try:
            exe = miners_mod.download(self.app_dir, self.key,
                                      progress=lambda d, t: self.progress.emit(d, t),
                                      log=self.logline.emit)
            self.ok.emit(exe)
        except Exception as exc:
            self.fail.emit(str(exc))


class MinePage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.symbol = ctx.cfg.selected_coin
        if self.symbol not in [c.symbol for c in ctx.coins()]:
            self.symbol = "PRL"
        self.runner = miners_mod.MinerRunner(self) if miners_mod.MinerRunner else None
        self.live_hash = 0.0
        self.started_at = 0.0
        self._dl = None
        self._repair_tried = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 20)
        root.setSpacing(14)
        root.addWidget(page_header("一键开挖", "填钱包地址 → 选矿池 → 开挖，其余参数自动生成"))

        body = QHBoxLayout()
        body.setSpacing(14)

        left = Card()
        left.body.setSpacing(13)

        self.coin_combo = ModernSelect()
        self.coin_combo.changed.connect(self._on_coin_changed)
        left.body.addWidget(field("币种", self.coin_combo))

        self.perf = PerfSlider(ctx.cfg.perf_pct)
        self.perf.changed.connect(self.ctx.set_perf)
        left.body.addWidget(self.perf)

        strip = QWidget()
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(16)
        self.st_price = KV("价格", "—")
        self.st_hash = KV("我的算力", "—")
        self.st_coin = KV("日产出", "—")
        self.st_rev = KV("日收益", "—")
        for kv in (self.st_price, self.st_hash, self.st_coin, self.st_rev):
            sl.addWidget(kv, 1)
        left.body.addWidget(strip)
        left.body.addWidget(Divider())

        self.wallet = QLineEdit()
        self.wallet.setPlaceholderText("粘贴你的收款地址，只需要这一项")
        self.wallet.setMinimumHeight(40)
        self.wallet.textChanged.connect(self._on_wallet_changed)
        left.body.addWidget(field("收款钱包地址", self.wallet))

        net_row = QWidget()
        nl = QHBoxLayout(net_row)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(8)
        nl.addWidget(label("收款网络", "label"))
        self.net_chip = Chip("—")
        self.net_chip.setFixedHeight(22)
        nl.addWidget(self.net_chip)
        nl.addStretch(1)
        left.body.addWidget(net_row)
        self.net_note = label("", "tiny")
        self.net_note.setWordWrap(True)
        left.body.addWidget(self.net_note)

        self.wallet_hint = label("", "tiny")
        self.wallet_hint.setWordWrap(True)
        left.body.addWidget(self.wallet_hint)

        self.pool_combo = ModernSelect()
        self.pool_combo.changed.connect(self._on_pool_changed)
        left.body.addWidget(field("矿池", self.pool_combo))
        self.pool_info = label("", "tiny")
        self.pool_info.setWordWrap(True)
        left.body.addWidget(self.pool_info)

        # 矿池详情
        detail = QFrame()
        detail.setObjectName("cardSoft")
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(12, 10, 12, 10)
        dl.setSpacing(8)
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(4)
        self.pool_fields = {}
        for i, (key, title) in enumerate([("region", "地区"), ("scheme", "结算模式"),
                                          ("fee", "费率"), ("payout", "打款周期"),
                                          ("minimum", "最低起付"), ("confirm", "到账确认")]):
            kv = KV(title, "—")
            grid.addWidget(kv, i // 2, i % 2)
            self.pool_fields[key] = kv
        dl.addLayout(grid)
        self.compat_chip = Chip("—")
        self.compat_chip.setFixedHeight(22)
        dl.addWidget(self.compat_chip, 0, Qt.AlignLeft)
        self.pool_coins = label("", "tiny")
        self.pool_coins.setWordWrap(True)
        dl.addWidget(self.pool_coins)
        self.pool_desc = label("", "tiny")
        self.pool_desc.setWordWrap(True)
        dl.addWidget(self.pool_desc)
        self.pool_link = QLabel("")
        self.pool_link.setOpenExternalLinks(True)
        dl.addWidget(self.pool_link)
        left.body.addWidget(detail)

        self.custom_box = QWidget()
        cl = QHBoxLayout(self.custom_box)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(8)
        self.custom_host = QLineEdit()
        self.custom_host.setPlaceholderText("矿池地址，如 cn.pearl.k1pool.com")
        self.custom_port = QLineEdit()
        self.custom_port.setPlaceholderText("端口")
        self.custom_port.setFixedWidth(96)
        self.custom_host.textChanged.connect(self._update_cmd)
        self.custom_port.textChanged.connect(self._update_cmd)
        cl.addWidget(self.custom_host, 1)
        cl.addWidget(self.custom_port)
        left.body.addWidget(self.custom_box)
        self.custom_box.hide()

        miner_box = QWidget()
        ml = QVBoxLayout(miner_box)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(8)
        row_top = QHBoxLayout()
        row_top.setContentsMargins(0, 0, 0, 0)
        row_top.setSpacing(8)
        self.miner_select = ModernSelect()
        self.miner_select.changed.connect(self._on_miner_changed)
        self.miner_state = Chip("检测中")
        row_top.addWidget(self.miner_select, 1)
        row_top.addWidget(self.miner_state)
        ml.addWidget(label("内核", "label"))
        ml.addLayout(row_top)

        row_btn = QHBoxLayout()
        row_btn.setContentsMargins(0, 0, 0, 0)
        row_btn.setSpacing(8)
        self.btn_download = QPushButton("下载内核")
        self.btn_download.setObjectName("ghost")
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.clicked.connect(self._download_miner)
        self.btn_pick = QPushButton("选择本地内核")
        self.btn_pick.setObjectName("ghost")
        self.btn_pick.setCursor(Qt.PointingHandCursor)
        self.btn_pick.clicked.connect(self._pick_miner)
        self.btn_repair = QPushButton("修复内核")
        self.btn_repair.setObjectName("ghost")
        self.btn_repair.setCursor(Qt.PointingHandCursor)
        self.btn_repair.setToolTip("用已下载的安装包重新解压（应对被杀软隔离）")
        self.btn_repair.clicked.connect(self._repair_miner)
        self.btn_edit_coin = QPushButton("编辑此币种")
        self.btn_edit_coin.setObjectName("link")
        self.btn_edit_coin.setCursor(Qt.PointingHandCursor)
        self.btn_edit_coin.clicked.connect(self._edit_coin)
        row_btn.addWidget(self.btn_edit_coin)
        row_btn.addStretch(1)
        row_btn.addWidget(self.btn_repair)
        row_btn.addWidget(self.btn_download)
        row_btn.addWidget(self.btn_pick)
        ml.addLayout(row_btn)
        left.body.addWidget(miner_box)

        self.btn_adv = QPushButton("高级参数 ▾")
        self.btn_adv.setObjectName("link")
        self.btn_adv.setCursor(Qt.PointingHandCursor)
        self.btn_adv.clicked.connect(self._toggle_adv)
        left.body.addWidget(self.btn_adv)

        self.adv_box = QWidget()
        al = QVBoxLayout(self.adv_box)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(8)
        self.worker = QLineEdit(self.ctx.cfg.worker)
        self.worker.textChanged.connect(self._on_worker)
        al.addWidget(field("矿工名（矿池显示用）", self.worker))
        self.extra = QLineEdit(self.ctx.cfg.extra_args)
        self.extra.textChanged.connect(self._on_extra)
        al.addWidget(field("附加参数", self.extra, "例如 --keepalive，留空即可"))
        self.adv_box.hide()
        left.body.addWidget(self.adv_box)

        self.cmd_label = QLabel("")
        self.cmd_label.setObjectName("mono")
        self.cmd_label.setWordWrap(True)
        self.cmd_label.setStyleSheet(
            f"color:{C.TEXT_3};background:{C.SURFACE_2};border:1px solid {C.BORDER};"
            f"border-radius:8px;padding:8px;font-size:11px;")
        left.body.addWidget(self.cmd_label)

        self.btn_start = QPushButton("一键开挖")
        self.btn_start.setObjectName("primary")
        self.btn_start.setMinimumHeight(46)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start)
        left.body.addStretch(1)

        body.addWidget(self._wrap_left(left), 3)

        right = QVBoxLayout()
        right.setSpacing(14)

        status = Card()
        top = QHBoxLayout()
        top.addWidget(h2("运行状态"))
        top.addStretch(1)
        self.state_chip = Chip("未开始", C.TEXT_2, "#F1F2F6")
        top.addWidget(self.state_chip)
        status.body.addLayout(top)

        self.live_value = QLabel("0 H/s")
        self.live_value.setObjectName("monoBig")
        status.body.addWidget(self.live_value)
        status.body.addWidget(label("实时算力（来自内核日志）", "tiny"))

        self.kv_est = KV("预计收益", "—")
        self.kv_live = KV("按实时算力", "—")
        self.kv_shares = KV("份额 接受 / 拒绝", "0 / 0")
        self.kv_time = KV("运行时长", "—")
        for kv in (self.kv_est, self.kv_live, self.kv_shares, self.kv_time):
            status.body.addWidget(kv)
        right.addWidget(status)

        logcard = Card()
        lh = QHBoxLayout()
        lh.addWidget(h2("运行日志"))
        lh.addStretch(1)
        self.btn_clear = QPushButton("清空")
        self.btn_clear.setObjectName("ghost")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(lambda: self.log_view.clear())
        self.btn_open = QPushButton("打开内核目录")
        self.btn_open.setObjectName("ghost")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_miner_dir)
        lh.addWidget(self.btn_clear)
        lh.addWidget(self.btn_open)
        logcard.body.addLayout(lh)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(240)
        logcard.body.addWidget(self.log_view, 1)
        right.addWidget(logcard, 1)

        body.addLayout(right, 2)
        root.addLayout(body, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

        if self.runner:
            self.runner.line.connect(self._on_line)
            self.runner.hashrate.connect(self._on_hash)
            self.runner.shares.connect(self._on_shares)
            self.runner.state.connect(self._on_state)

        self._reload_coins()
        self.ctx.coinsChanged.connect(self._reload_coins)

    # ------------------------------------------------------------------ 布局
    def _wrap_left(self, card):
        """左栏：可滚动的设置卡片 + 底部常驻的开挖按钮。"""
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(card)
        lay.addWidget(scroll, 1)
        lay.addWidget(self.btn_start)
        return holder

    # ------------------------------------------------------------------ 币种
    def _reload_coins(self):
        coins = self.ctx.coins()
        symbols = [c.symbol for c in coins]
        if self.symbol not in symbols:
            self.symbol = "PRL" if "PRL" in symbols else symbols[0]
        self.coin_combo.blockSignals(True)
        self.coin_combo.clear()
        for c in coins:
            self.coin_combo.addItem(f"{c.symbol} · {c.name_cn}")
        self.coin_combo.setCurrentIndex(symbols.index(self.symbol))
        self.coin_combo.blockSignals(False)
        self._on_coin_changed(self.coin_combo.currentIndex())

    def select_coin(self, symbol):
        symbols = [c.symbol for c in self.ctx.coins()]
        if symbol in symbols:
            self.symbol = symbol
            self.coin_combo.setCurrentIndex(symbols.index(symbol))

    def _coin(self):
        return self.ctx.coin(self.symbol)

    def _on_coin_changed(self, _idx):
        c = self.ctx.coins()[max(0, self.coin_combo.currentIndex())]
        self.symbol = c.symbol
        self.ctx.cfg.selected_coin = c.symbol
        self.ctx.save()

        self.wallet.blockSignals(True)
        self.wallet.setText(self.ctx.cfg.wallets.get(c.symbol, ""))
        self.wallet.blockSignals(False)
        self._on_wallet_changed(self.wallet.text())

        self.pool_combo.blockSignals(True)
        self.pool_combo.clear()
        for p in pools_for(c):
            self.pool_combo.addItem(f"{p.name} · {p.host}" if p.host else p.name)
        self.pool_combo.blockSignals(False)
        self.btn_edit_coin.setVisible(c.custom)

        opts = miners_for(c)
        self.miner_select.blockSignals(True)
        self.miner_select.clear()
        for k in opts:
            self.miner_select.addItem(MINERS[k].name)
        key = self._miner_key()
        if key in opts:
            self.miner_select.setCurrentIndex(opts.index(key))
        self.miner_select.blockSignals(False)

        self._on_pool_changed(0)
        self._update_miner_state()
        self.refresh()

    def _edit_coin(self):
        from ..catalog import COIN_BY_SYMBOL  # noqa: F401
        for d in self.ctx.cfg.custom_coins:
            if (d.get("symbol") or "").upper() == self.symbol.upper():
                CustomCoinDialog(self.ctx, d, self).exec()
                self.refresh()
                return

    def _update_wallet_info(self):
        c = self._coin()
        pools = pools_for(c)
        idx = max(0, self.pool_combo.currentIndex())
        pool = pools[idx] if idx < len(pools) else pools[0]

        if pool.wallet_mode == "account":
            self.net_chip.set_state("矿池账户名", C.AMBER, C.AMBER_SOFT)
            self.net_note.setText("该矿池用账户名挖矿：这里填注册用户名，收益先记在矿池，"
                                  "提现时再在矿池后台选择 PRL 主网地址")
            self.wallet_hint.setText("填你注册的 f2pool 用户名")
            return

        if c.custom:
            net = c.data.get("network") or "自定义网络"
            fmt, warn = "按该币种官方格式", "确认钱包与矿池使用同一条链"
        else:
            net, fmt, warn = WALLET_NET.get(c.symbol, ("—", "—", ""))
        self.net_chip.set_state(net, C.ACCENT, C.ACCENT_SOFT)
        self.net_note.setText(f"地址格式：{fmt}。{warn}")
        self.wallet_hint.setText(WALLET_HINT.get(c.symbol, "填写该币种的收款地址"))

    def _on_pool_changed(self, idx):
        c = self._coin()
        pools = pools_for(c)
        pool = pools[idx] if 0 <= idx < len(pools) else pools[0]
        is_custom_pool = not pool.host
        self.custom_box.setVisible(is_custom_pool)
        if is_custom_pool and c.custom and c.data.get("pool_host"):
            self.custom_host.setText(c.data.get("pool_host", ""))
            self.custom_port.setText(str(c.data.get("pool_port") or ""))

        meta = " · ".join(x for x in (pool.scheme, pool.fee and f"费率 {pool.fee}",
                                      pool.payout, pool.minimum and f"起付 {pool.minimum}",
                                      pool.confirm) if x)
        if pool.wallet_mode == "account":
            meta = "该矿池用账户名挖矿，填注册用户名而不是钱包地址 · " + meta
        self.pool_info.setText(meta)

        self.pool_fields["region"].set(pool.region or "—")
        self.pool_fields["scheme"].set(pool.scheme or "—")
        self.pool_fields["fee"].set(pool.fee or "—")
        self.pool_fields["payout"].set(pool.payout or "—")
        self.pool_fields["minimum"].set(pool.minimum or "—")
        self.pool_fields["confirm"].set(pool.confirm or "—")

        if pool.coins:
            supported = c.symbol in pool.coins
            self.compat_chip.setVisible(True)
            if supported:
                self.compat_chip.set_state(f"✓ 该池支持 {c.symbol}", C.GREEN, C.GREEN_SOFT)
            else:
                self.compat_chip.set_state(f"✗ 该池不支持 {c.symbol}", C.RED, C.RED_SOFT)
            self.pool_coins.setText("支持币种：" + " · ".join(pool.coins))
        else:
            self.compat_chip.setVisible(False)
            self.pool_coins.setText("")

        self.pool_desc.setText(pool.desc or "")
        if pool.url:
            self.pool_link.setText(f'<a href="{pool.url}" style="color:{C.ACCENT};'
                                   f'text-decoration:none;font-size:11px;">查看矿池官网 / 教程</a>')
        else:
            self.pool_link.setText("")

        self.wallet_hint.setText(
            "该矿池使用账户名挖矿：填你注册的 f2pool 用户名" if pool.wallet_mode == "account"
            else WALLET_HINT.get(c.symbol, "填写该币种的收款地址"))
        self._update_wallet_info()
        self._update_cmd()

    def _min_wallet_len(self):
        c = self._coin()
        pools = pools_for(c)
        idx = max(0, self.pool_combo.currentIndex())
        pool = pools[idx] if idx < len(pools) else pools[0]
        return 3 if pool.wallet_mode == "account" else 20

    def _on_wallet_changed(self, text):
        ok = len(text.strip()) >= self._min_wallet_len()
        self.wallet.setProperty("invalid", "false" if (ok or not text) else "true")
        self.wallet.style().unpolish(self.wallet)
        self.wallet.style().polish(self.wallet)
        if ok:
            self.ctx.cfg.wallets[self.symbol] = text.strip()
            self.ctx.save()
        self._update_cmd()

    def _on_worker(self, text):
        self.ctx.cfg.worker = text.strip() or "rig01"
        self.ctx.save()
        self._update_cmd()

    def _on_extra(self, text):
        self.ctx.cfg.extra_args = text
        self.ctx.save()
        self._update_cmd()

    def _toggle_adv(self):
        vis = not self.adv_box.isVisible()
        self.adv_box.setVisible(vis)
        self.btn_adv.setText("高级参数 ▴" if vis else "高级参数 ▾")

    def _pool_target(self):
        c = self._coin()
        pools = pools_for(c)
        idx = max(0, self.pool_combo.currentIndex())
        pool = pools[idx] if idx < len(pools) else None
        if pool and pool.host:
            return pool.host, pool.port
        host = self.custom_host.text().strip()
        try:
            port = int(self.custom_port.text().strip() or 0)
        except ValueError:
            port = 0
        return host, port

    def _miner_key(self):
        c = self._coin()
        opts = miners_for(c)
        chosen = self.ctx.cfg.miner_choice.get(c.symbol)
        if chosen in opts:
            return chosen
        if c.custom:
            return c.data.get("miner") or opts[0]
        return COIN_MINER.get(c.symbol, opts[0])

    def _on_miner_changed(self, idx):
        opts = miners_for(self._coin())
        if 0 <= idx < len(opts):
            self.ctx.cfg.miner_choice[self.symbol] = opts[idx]
            self.ctx.save()
        self._update_miner_state()
        self._update_cmd()

    def _miner_exe(self):
        key = self._miner_key()
        path = self.ctx.cfg.miner_paths.get(key)
        if path and os.path.exists(path):
            return path
        exe = miners_mod.find_installed(self.ctx.app_dir, key)
        if exe:
            return exe
        # 安装包还在、exe 却没了（常见于被杀软隔离）——自动重新解压一次
        if key not in self._repair_tried:
            self._repair_tried.add(key)
            try:
                exe = miners_mod.repair(self.ctx.app_dir, key)
                self.ctx.cfg.miner_paths[key] = exe
                self.ctx.save()
                return exe
            except Exception:
                return None
        return None

    def _update_miner_state(self):
        key = self._miner_key()
        exe = self._miner_exe()
        if exe:
            self.miner_state.set_state(f"{MINERS[key].name} 已就绪", C.GREEN, C.GREEN_SOFT)
            self.btn_download.setText("重新下载")
        else:
            self.miner_state.set_state(f"{MINERS[key].name} 未安装", C.AMBER, C.AMBER_SOFT)
            self.btn_download.setText("下载内核")

    def _update_cmd(self):
        c = self._coin()
        host, port = self._pool_target()
        wallet = self.wallet.text().strip() or "你的钱包地址"
        key = self._miner_key()
        args = build_args(c, key, host or "HOST", port or 0, wallet,
                          self.ctx.cfg.worker, self.ctx.cfg.extra_args)
        name = MINERS[key].exe
        self.cmd_label.setText(f"{name} " + (" ".join(args) if args else "（该币种暂未内置命令行模板）"))

    # ------------------------------------------------------------------ 数据
    def refresh(self):
        ctx = self.ctx
        self.perf.set_value(ctx.cfg.perf_pct)
        c = self._coin()
        p = ctx.profit(c)
        cm = ctx._market_for(c)
        self.st_price.set(f"${cm.price_usd:,.6g}" if cm else "—")
        self.st_hash.set(fmt_hash(p.hashrate) if p else "—")
        self.st_coin.set(f"{profit_mod.fmt_num(p.coin_day, c.digits)} {c.symbol}" if p else "—")
        self.st_rev.set(ctx.money(ctx.revenue_cny(p)) if p else "—", C.GREEN)
        if p:
            self.kv_est.set(f"{ctx.money(ctx.revenue_cny(p))} / {ctx.cfg.unit}", C.GREEN)
        else:
            self.kv_est.set("—")
        self._update_miner_state()
        self._update_cmd()

    # ------------------------------------------------------------------ 运行
    def _append(self, text):
        self.log_view.appendPlainText(text)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_line(self, text):
        self._append(text)

    def _on_hash(self, h):
        self.live_hash = h
        self.live_value.setText(fmt_hash(h))
        c = self._coin()
        p = self.ctx.profit(c)
        if p and p.hashrate > 0:
            live_day = self.ctx.revenue_cny(p) * h / p.hashrate
            self.kv_live.set(f"{self.ctx.money(live_day)} / {self.ctx.cfg.unit}", C.GREEN)

    def _on_shares(self, ok, bad):
        self.kv_shares.set(f"{ok} / {bad}")

    def _on_state(self, st):
        if st == "running":
            self.state_chip.set_state("运行中", C.GREEN, C.GREEN_SOFT)
            self.started_at = time.time()
            self.btn_start.setText("停止挖矿")
            self.btn_start.setStyleSheet(
                f"background:{C.RED};color:#FFF;border:none;border-radius:10px;"
                f"padding:11px 20px;font-weight:600;")
        elif st in ("stopped", "error"):
            self.state_chip.set_state("已停止" if st == "stopped" else "异常",
                                      C.TEXT_2 if st == "stopped" else C.RED,
                                      "#F1F2F6" if st == "stopped" else C.RED_SOFT)
            self.live_value.setText("0 H/s")
            self.started_at = 0.0
            self.btn_start.setText("一键开挖")
            self.btn_start.setStyleSheet("")

    def _tick(self):
        if self.started_at:
            sec = int(time.time() - self.started_at)
            self.kv_time.set(f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}")
        else:
            self.kv_time.set("—")

    def on_start(self):
        if self.runner and self.runner.running():
            self.runner.stop()
            self._append("--- 已请求停止 ---")
            return
        if not self.runner:
            self._append("内核运行组件不可用")
            return
        if self.ctx.cfg.perf_pct <= 0:
            self._append("性能占用为 0%，先把滑块调高再开挖")
            return

        c = self._coin()
        wallet = self.wallet.text().strip()
        if len(wallet) < self._min_wallet_len():
            self._on_wallet_changed(wallet)
            self._append("请先填写收款地址（F2Pool 这类账户池填用户名即可）")
            self.wallet.setFocus()
            return

        host, port = self._pool_target()
        if not host or not port:
            self._append("请选择一个矿池，或填写自定义矿池地址和端口")
            self.custom_box.show()
            return

        key = self._miner_key()
        exe = self._miner_exe()
        if not exe:
            self._append(f"未检测到 {MINERS[key].name}，正在自动下载…")
            self._download_miner(auto_start=True)
            return
        self._launch(exe, host, port, wallet)

    def _launch(self, exe, host, port, wallet):
        c = self._coin()
        args = build_args(c, self._miner_key(), host, port, wallet,
                          self.ctx.cfg.worker, self.ctx.cfg.extra_args)
        if not args:
            self._append("该币种暂未内置命令行模板，请使用「选择本地内核」并手动配置")
            return
        self._append(f"$ {os.path.basename(exe)} " + " ".join(args))
        if self.ctx.cfg.limit_power:
            self._apply_power_limit()
        if not self.runner.start(exe, args, os.path.dirname(exe)):
            self._append("启动失败：可能是 Windows 安全中心拦截了挖矿内核（常见误报）")
            self._append("处理办法：安全中心 → 病毒和威胁防护 → 管理设置 → 排除项 → "
                         "添加文件夹 miners，然后重试")

    def _apply_power_limit(self):
        """按性能占用百分比设置 NVIDIA 功耗墙（需要管理员权限）。"""
        watt = int(self.ctx.gpu_model.tdp * self.ctx.perf)
        try:
            import subprocess
            out = subprocess.run(["nvidia-smi", "-pl", str(watt)], capture_output=True,
                                 text=True, timeout=8,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            msg = (out.stdout or out.stderr).strip().splitlines()
            self._append(f"功耗墙 -> {watt}W: {msg[-1] if msg else out.returncode}")
        except Exception as exc:
            self._append(f"设置功耗墙失败（通常需要管理员权限）: {exc}")

    # ------------------------------------------------------------------ 内核
    def _download_miner(self, auto_start=False):
        key = self._miner_key()
        if self._dl and self._dl.isRunning():
            return
        self.miner_state.set_state("下载中…", C.ACCENT, C.ACCENT_SOFT)
        self._dl = _Downloader(self.ctx.app_dir, key, self)
        self._dl.logline.connect(self._append)
        self._dl.progress.connect(self._on_dl_progress)
        self._dl.ok.connect(lambda exe: self._on_dl_ok(exe, auto_start))
        self._dl.fail.connect(self._on_dl_fail)
        self._dl.start()

    def _on_dl_progress(self, done, total):
        if total:
            self.miner_state.set_state(f"下载中 {done * 100 // total}%", C.ACCENT, C.ACCENT_SOFT)

    def _on_dl_ok(self, exe, auto_start):
        self.ctx.cfg.miner_paths[self._miner_key()] = exe
        self.ctx.save()
        self._update_miner_state()
        self._append(f"内核已就绪: {exe}")
        if auto_start:
            host, port = self._pool_target()
            self._launch(exe, host, port, self.wallet.text().strip())

    def _on_dl_fail(self, msg):
        self._update_miner_state()
        self._append(f"下载失败: {msg}")
        self._append("可手动下载后点「选择本地内核」指定 exe 路径")

    def _pick_miner(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择内核可执行文件", "",
                                              "可执行文件 (*.exe);;所有文件 (*.*)")
        if path:
            self.ctx.cfg.miner_paths[self._miner_key()] = path
            self.ctx.save()
            self._update_miner_state()
            self._append(f"已指定内核: {path}")

    def _repair_miner(self):
        key = self._miner_key()
        self._append("正在用本地安装包重新解压内核…")
        try:
            exe = miners_mod.repair(self.ctx.app_dir, key)
        except Exception as exc:
            self._append(f"修复失败：{exc}")
            ans = QMessageBox.question(
                self, "内核被拦截？",
                "重新解压后仍未找到内核 exe，通常是 Windows 安全中心把它隔离了。\n\n"
                "是否现在添加 Defender 排除项？（会弹出 UAC，需要管理员确认）",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if ans == QMessageBox.Yes:
                self._append("正在请求添加 Defender 排除项…")
                try:
                    miners_mod.add_defender_exclusion(self.ctx.app_dir)
                    self._append("已提交排除项；2 秒后自动重试解压")
                    time.sleep(2)
                    exe = miners_mod.repair(self.ctx.app_dir, key)
                except Exception as exc2:
                    self._append(f"排除项添加失败：{exc2}")
                    return
            else:
                return
        self.ctx.cfg.miner_paths[key] = exe
        self.ctx.save()
        self._update_miner_state()
        self._append(f"内核已就绪: {exe}")

    def _open_miner_dir(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(miners_mod.miner_root(self.ctx.app_dir)))


# ====================================================================== 设置
class SettingsPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 20)
        root.setSpacing(14)
        root.addWidget(page_header("设置", "口径、性能、数据源"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        c0 = Card()
        c0.body.addWidget(h2("性能占用"))
        self.perf = PerfSlider(ctx.cfg.perf_pct, show_title=False)
        self.perf.changed.connect(self.ctx.set_perf)
        c0.body.addWidget(self.perf)
        self.limit_power = QCheckBox("开挖时按占用率自动设置功耗墙（nvidia-smi，需要管理员）")
        self.limit_power.setChecked(ctx.cfg.limit_power)
        self.limit_power.stateChanged.connect(self._on_limit)
        c0.body.addWidget(self.limit_power)
        lay.addWidget(c0)

        c1 = Card()
        c1.body.addWidget(h2("收益口径"))
        self.use_elec = QCheckBox("扣除电费（默认只看毛收益）")
        self.use_elec.setChecked(ctx.cfg.use_electricity)
        self.use_elec.stateChanged.connect(self._toggle_elec)
        c1.body.addWidget(self.use_elec)
        row = QHBoxLayout()
        self.elec = QDoubleSpinBox()
        self.elec.setRange(0, 5)
        self.elec.setSingleStep(0.05)
        self.elec.setDecimals(2)
        self.elec.setValue(ctx.cfg.electricity)
        self.elec.setSuffix(" 元/度")
        self.elec.setEnabled(ctx.cfg.use_electricity)
        self.elec.valueChanged.connect(self._on_elec)
        self.usd = QDoubleSpinBox()
        self.usd.setRange(1, 20)
        self.usd.setSingleStep(0.1)
        self.usd.setDecimals(2)
        self.usd.setValue(ctx.cfg.usd_cny)
        self.usd.setPrefix("1 USD = ")
        self.usd.setSuffix(" CNY")
        self.usd.valueChanged.connect(self._on_usd)
        row.addWidget(field("电价", self.elec), 1)
        row.addWidget(field("汇率", self.usd), 1)
        c1.body.addLayout(row)
        lay.addWidget(c1)

        c2 = Card()
        c2.body.addWidget(h2("显卡与算力"))
        self.gpu_combo = ModernSelect()
        self.gpu_combo.addItem("自动检测")
        from ..catalog import GPUS
        for g in GPUS:
            self.gpu_combo.addItem(g.name)
        keys = ["auto"] + [g.key for g in GPUS]
        self._gpu_keys = keys
        if ctx.cfg.gpu_key in keys:
            self.gpu_combo.setCurrentIndex(keys.index(ctx.cfg.gpu_key))
        self.gpu_combo.changed.connect(self._on_gpu)
        c2.body.addWidget(field("显卡型号", self.gpu_combo,
                                f"当前检测：{ctx.gpu.name}（{ctx.gpu.source}）"))

        row2 = QHBoxLayout()
        self.power = QSpinBox()
        self.power.setRange(0, 1500)
        self.power.setSingleStep(5)
        self.power.setSuffix(" W")
        self.power.setSpecialValueText("跟随检测")
        self.power.setValue(ctx.cfg.power_limit)
        self.power.valueChanged.connect(self._on_power)
        row2.addWidget(field("参考功耗（仅电费口径用）", self.power), 1)

        self.cal_coin = ModernSelect()
        for c in ctx.coins():
            self.cal_coin.addItem(f"{c.symbol} · {c.unit}")
        self.cal_coin.changed.connect(self.refresh)
        row2.addWidget(field("算力校准币种", self.cal_coin), 1)
        self.cal_value = QLineEdit()
        self.cal_value.setPlaceholderText("留空 = 用参考算力，可填 95e12")
        self.cal_value.editingFinished.connect(self._on_cal)
        row2.addWidget(field("我的实测算力", self.cal_value), 1)
        c2.body.addLayout(row2)
        lay.addWidget(c2)

        c3 = Card()
        top3 = QHBoxLayout()
        top3.addWidget(h2("自定义币种"))
        top3.addStretch(1)
        b_add = QPushButton("＋ 新建")
        b_add.setObjectName("ghost")
        b_add.setCursor(Qt.PointingHandCursor)
        b_add.clicked.connect(self._add_custom)
        top3.addWidget(b_add)
        c3.body.addLayout(top3)
        self.custom_list = QVBoxLayout()
        self.custom_list.setSpacing(6)
        c3.body.addLayout(self.custom_list)
        lay.addWidget(c3)

        c4 = Card()
        c4.body.addWidget(h2("数据源"))
        self.ds_label = label("", "muted")
        c4.body.addWidget(self.ds_label)
        row4 = QHBoxLayout()
        self.price_rate = ModernSelect()
        for sec in (3, 5, 10, 30, 60):
            self.price_rate.addItem(f"价格每 {sec} 秒刷新")
        idx = [3, 5, 10, 30, 60].index(ctx.cfg.price_refresh_sec) \
            if ctx.cfg.price_refresh_sec in (3, 5, 10, 30, 60) else 0
        self.price_rate.setCurrentIndex(idx)
        self.price_rate.changed.connect(self._on_price_rate)
        row4.addWidget(field("刷新频率", self.price_rate), 1)
        row4.addStretch(1)
        c4.body.addLayout(row4)

        row3 = QHBoxLayout()
        b1 = QPushButton("立即刷新行情")
        b1.setObjectName("ghost")
        b1.setCursor(Qt.PointingHandCursor)
        b1.clicked.connect(lambda: self.ctx.refresh_async())
        b2 = QPushButton("清除本地缓存")
        b2.setObjectName("ghost")
        b2.setCursor(Qt.PointingHandCursor)
        b2.clicked.connect(self._clear_cache)
        row3.addWidget(b1)
        row3.addWidget(b2)
        row3.addStretch(1)
        c4.body.addLayout(row3)
        lay.addWidget(c4)

        c5 = Card()
        c5.body.addWidget(h2("教程与数据来源"))
        for name, url in REFERENCES:
            lb = QLabel(f'<a href="{url}" style="color:{C.ACCENT};text-decoration:none;">{name}</a>')
            lb.setOpenExternalLinks(True)
            lb.setStyleSheet("font-size:12px;")
            c5.body.addWidget(lb)
        lay.addWidget(c5)

        c6 = Card()
        c6.body.addWidget(h2("关于"))
        c6.body.addWidget(label("Ciallo～(∠・ω< )⌒☆ v1.1 · 本地显卡挖矿工具", "muted"))
        c6.body.addWidget(label("行情：whattomine / CoinGecko / CoinPaprika · "
                                "内核：lpminer / SRBMiner-Multi / lolMiner", "tiny"))
        lay.addWidget(c6)

        lay.addStretch(1)
        scroll.setWidget(holder)
        root.addWidget(scroll, 1)
        self._rebuild_custom()
        ctx.coinsChanged.connect(self._rebuild_custom)
        self.refresh()

    # ------------------------------------------------------------------
    def _rebuild_custom(self):
        while self.custom_list.count():
            item = self.custom_list.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        customs = self.ctx.cfg.custom_coins
        if not customs:
            self.custom_list.addWidget(label("还没有自定义币种，点右上角「＋ 新建」添加", "tiny"))
            return
        for d in customs:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            rl.setSpacing(8)
            sym = QLabel((d.get("symbol") or "").upper())
            sym.setStyleSheet("font-weight:700;font-size:12px;")
            sym.setFixedWidth(52)
            rl.addWidget(sym)
            rl.addWidget(label(f"{d.get('name', '')} · {d.get('algo', '')}", "tiny"))
            rl.addStretch(1)
            be = QPushButton("编辑")
            be.setObjectName("ghost")
            be.setCursor(Qt.PointingHandCursor)
            be.clicked.connect(lambda _=False, dd=d: self._edit_custom(dd))
            bd = QPushButton("删除")
            bd.setObjectName("danger")
            bd.setCursor(Qt.PointingHandCursor)
            bd.clicked.connect(lambda _=False, dd=d: self.ctx.remove_custom(dd.get("symbol", "")))
            rl.addWidget(be)
            rl.addWidget(bd)
            self.custom_list.addWidget(row)

    def _add_custom(self):
        CustomCoinDialog(self.ctx, None, self).exec()

    def _edit_custom(self, data):
        CustomCoinDialog(self.ctx, data, self).exec()

    def _on_price_rate(self, idx):
        rates = (3, 5, 10, 30, 60)
        self.ctx.cfg.price_refresh_sec = rates[idx] if 0 <= idx < len(rates) else 3
        self.ctx.save()

    def _on_limit(self, state):
        self.ctx.cfg.limit_power = bool(state)
        self.ctx.save()

    def _toggle_elec(self, state):
        self.ctx.cfg.use_electricity = bool(state)
        self.elec.setEnabled(bool(state))
        self.ctx.save()
        self.ctx.displayChanged.emit()

    def _on_elec(self, v):
        self.ctx.cfg.electricity = float(v)
        self.ctx.save()
        self.ctx.displayChanged.emit()

    def _on_usd(self, v):
        self.ctx.cfg.usd_cny = float(v)
        self.ctx.save()
        self.ctx.displayChanged.emit()

    def _on_gpu(self, idx):
        key = self._gpu_keys[idx]
        self.ctx.cfg.gpu_key = "" if key == "auto" else key
        self.ctx.gpu_key = key if key != "auto" else (self.ctx.gpu.key or "rtx4070lap")
        self.ctx.save()
        self.ctx.displayChanged.emit()

    def _on_power(self, v):
        self.ctx.cfg.power_limit = int(v)
        self.ctx.save()
        self.ctx.displayChanged.emit()

    def _on_cal(self):
        coins = self.ctx.coins()
        if not coins:
            return
        sym = coins[min(self.cal_coin.currentIndex(), len(coins) - 1)].symbol
        txt = self.cal_value.text().strip()
        if not txt:
            self.ctx.cfg.hash_overrides.pop(sym, None)
        else:
            try:
                self.ctx.cfg.hash_overrides[sym] = float(txt)
            except ValueError:
                self.cal_value.setText("")
                return
        self.ctx.save()
        self.ctx.displayChanged.emit()

    def _clear_cache(self):
        path = os.path.join(self.ctx.app_dir, "data", "market_cache.json")
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
        self.ctx.refresh_async()

    def refresh(self):
        self.ds_label.setText(self.ctx.status_line())
        self.perf.set_value(self.ctx.cfg.perf_pct)
        coins = self.ctx.coins()
        if coins:
            sym = coins[min(self.cal_coin.currentIndex(), len(coins) - 1)].symbol
            v = self.ctx.cfg.hash_overrides.get(sym)
            self.cal_value.setText(f"{v:.6g}" if v else "")

