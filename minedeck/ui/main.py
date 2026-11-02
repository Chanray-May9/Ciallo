"""主窗口：侧边导航 + 顶部单位切换 + 四个页面。"""

import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

from ..assets import APP_NAME, asset_path
from ..theme import C, QSS
from .pages import CoinsPage, DashboardPage, MinePage, SettingsPage
from .widgets import LogoMark, Segmented, label


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(f"{APP_NAME} · 显卡挖矿工作台")
        self.resize(1290, 860)
        self.setMinimumSize(1120, 740)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ------------------------------------------------ 侧边栏
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(212)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(16, 20, 16, 16)
        sl.setSpacing(6)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = LogoMark(asset_path("logo.png"), 32, 10)
        brand.addWidget(mark)
        bt = QVBoxLayout()
        bt.setSpacing(0)
        title = QLabel("Ciallo～(∠・ω< )⌒☆")
        title.setObjectName("brandTitle")
        title.setStyleSheet("font-size:11px;font-weight:700;")
        title.setToolTip(APP_NAME)
        sub = QLabel("显卡挖矿工作台")
        sub.setObjectName("brandSub")
        bt.addWidget(title)
        bt.addWidget(sub)
        brand.addLayout(bt)
        brand.addStretch(1)
        sl.addLayout(brand)
        sl.addSpacing(18)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []
        for i, (txt, hint) in enumerate([("概览", "收益与行情"), ("币种收益", "全币种对比"),
                                         ("一键开挖", "钱包 + 矿池"), ("设置", "口径与硬件")]):
            b = QPushButton(f"{txt}")
            b.setObjectName("navBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(36)
            b.setToolTip(hint)
            self.nav_group.addButton(b, i)
            self.nav_buttons.append(b)
            sl.addWidget(b)
        self.nav_buttons[0].setChecked(True)

        sl.addStretch(1)

        self.side_status = QLabel("")
        self.side_status.setWordWrap(True)
        self.side_status.setStyleSheet(f"color:{C.TEXT_3};font-size:11px;line-height:1.4;")
        sl.addWidget(self.side_status)
        ver = QLabel("v1.0 · 本地运行，不上传数据")
        ver.setStyleSheet(f"color:{C.TEXT_3};font-size:10px;")
        sl.addWidget(ver)

        lay.addWidget(side)

        # ------------------------------------------------ 右侧
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        top = QWidget()
        top.setFixedHeight(54)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(26, 0, 22, 0)
        tl.setSpacing(10)
        self.top_status = QLabel("")
        self.top_status.setStyleSheet(f"color:{C.TEXT_3};font-size:12px;")
        tl.addWidget(self.top_status)
        tl.addStretch(1)

        tl.addWidget(label("单位", "tiny"))
        self.unit_seg = Segmented(["小时", "天", "周", "月", "年"], ctx.cfg.unit)
        self.unit_seg.setFixedHeight(32)
        self.unit_seg.changed.connect(self._on_unit)
        tl.addWidget(self.unit_seg)

        tl.addSpacing(6)
        self.cur_seg = Segmented(["¥ CNY", "$ USD"], "¥ CNY" if ctx.cfg.currency == "CNY" else "$ USD")
        self.cur_seg.setFixedHeight(32)
        self.cur_seg.changed.connect(self._on_cur)
        tl.addWidget(self.cur_seg)

        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setObjectName("ghost")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._refresh)
        tl.addWidget(self.btn_refresh)

        right.addWidget(top)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{C.BORDER};")
        right.addWidget(line)

        self.stack = QStackedWidget()
        self.page_dash = DashboardPage(ctx)
        self.page_coins = CoinsPage(ctx)
        self.page_mine = MinePage(ctx)
        self.page_settings = SettingsPage(ctx)
        for p in (self.page_dash, self.page_coins, self.page_mine, self.page_settings):
            self.stack.addWidget(p)
        right.addWidget(self.stack, 1)

        lay.addLayout(right, 1)

        # ------------------------------------------------ 事件
        self.nav_group.idClicked.connect(self._switch)
        self.page_coins.open_mine.connect(self._open_mine)

        ctx.marketChanged.connect(self._refresh_all)
        ctx.displayChanged.connect(self._refresh_all)
        ctx.configChanged.connect(self._refresh_all)

        self.clock = QTimer(self)
        self.clock.timeout.connect(self._tick)
        self.clock.start(1000)

        self.auto = QTimer(self)
        self.auto.timeout.connect(self._refresh)
        self.auto.start(max(15, ctx.cfg.refresh_sec) * 1000)

        # 价格 3 秒轮询（只看价格，不拉全网数据）
        self.price_timer = QTimer(self)
        self.price_timer.timeout.connect(self.ctx.refresh_prices_async)
        self.price_timer.start(max(3, ctx.cfg.price_refresh_sec) * 1000)

        # 每秒采样一次曲线，图表跟着实时刷新
        self.sampler = QTimer(self)
        self.sampler.timeout.connect(self._sample)
        self.sampler.start(1000)

        QTimer.singleShot(250, self._refresh)
        self._refresh_all()

    # ------------------------------------------------------------------
    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 2:
            self.page_mine.refresh()
        if idx == 3:
            self.page_settings.refresh()

    def _open_mine(self, symbol):
        self.page_mine.select_coin(symbol)
        self.nav_buttons[2].setChecked(True)
        self.stack.setCurrentIndex(2)

    def _on_unit(self, unit):
        self.ctx.set_display(unit=unit)

    def _on_cur(self, val):
        self.ctx.set_display(currency="USD" if "USD" in val else "CNY")

    def _refresh(self):
        if not self.ctx.refresh_async():
            return
        self.btn_refresh.setEnabled(False)
        QTimer.singleShot(400, lambda: self.btn_refresh.setEnabled(True))

    def _sample(self):
        self.ctx.sample_history()
        self.page_dash.refresh()

    def _tick(self):
        self.top_status.setText(self.ctx.status_line())

    def _refresh_all(self):
        for p in (self.page_dash, self.page_coins, self.page_mine, self.page_settings):
            try:
                p.refresh()
            except Exception:
                pass
        self.top_status.setText(self.ctx.status_line())
        ts = (time.strftime("%H:%M:%S", time.localtime(self.ctx.last_update))
              if self.ctx.last_update else "--:--:--")
        self.side_status.setText(f"数据源 {self.ctx.market.source}\n更新 {ts}")
        interval = max(3, self.ctx.cfg.price_refresh_sec) * 1000
        if self.price_timer.interval() != interval:
            self.price_timer.start(interval)
