"""通用 UI 组件（极简浅色风格）。"""

import time

from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QPoint, QTimer
from PySide6.QtGui import (QColor, QPainter, QPainterPath, QLinearGradient, QFont, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget, QButtonGroup, QSizePolicy, QSlider)

from ..theme import C


# ------------------------------------------------------------------ 基础
class Card(QFrame):
    def __init__(self, parent=None, padding=18, spacing=12, soft=False):
        super().__init__(parent)
        self.setObjectName("cardSoft" if soft else "card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(spacing)


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class PerfSlider(QWidget):
    """显卡性能占用百分比滑块（0-100）。"""

    changed = Signal(int)

    def __init__(self, value=100, show_title=True, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        if show_title:
            self.title = label("性能占用", "label")
            lay.addWidget(self.title)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(value))
        self.slider.setSingleStep(5)
        self.slider.setPageStep(10)
        self.slider.setCursor(Qt.PointingHandCursor)
        self.slider.setMinimumWidth(120)
        lay.addWidget(self.slider, 1)
        self.vl = QLabel(f"{int(value)}%")
        self.vl.setFixedWidth(44)
        self.vl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.vl.setStyleSheet(f"font-family:{C.MONO};font-size:12px;font-weight:600;")
        lay.addWidget(self.vl)
        self.slider.valueChanged.connect(self._on_change)

    def _on_change(self, v):
        self.vl.setText(f"{v}%")
        self.vl.setStyleSheet(f"font-family:{C.MONO};font-size:12px;font-weight:600;"
                              f"color:{C.TEXT if v > 0 else C.RED};")
        self.changed.emit(int(v))

    def set_value(self, v):
        v = int(v)
        self.slider.blockSignals(True)
        self.slider.setValue(v)
        self.slider.blockSignals(False)
        self.vl.setText(f"{v}%")


class _SelectBox(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("select")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(38)
        self.setAttribute(Qt.WA_Hover, True)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(ev)


class ModernSelect(QWidget):
    """自绘下拉选择器：圆角弹层 + 悬停高亮，替掉系统风格 QComboBox。"""

    changed = Signal(int)

    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self._items = list(items or [])
        self._index = 0
        self._popup = None
        self._closed_at = 0.0

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.box = _SelectBox()
        bl = QHBoxLayout(self.box)
        bl.setContentsMargins(12, 9, 12, 9)
        bl.setSpacing(8)
        self.text_label = QLabel("-")
        self.text_label.setStyleSheet("font-size:13px;")
        self.arrow = QLabel("▾")
        self.arrow.setStyleSheet(f"color:{C.TEXT_3};font-size:11px;")
        bl.addWidget(self.text_label, 1)
        bl.addWidget(self.arrow)
        self.box.clicked.connect(self._open)
        lay.addWidget(self.box)
        self._sync_text()

    # ---------------------------------------------------------------- API
    def addItem(self, text):
        self._items.append(text)
        self._sync_text()

    def addItems(self, texts):
        for t in texts:
            self.addItem(t)

    def clear(self):
        self._items = []
        self._index = 0
        self._sync_text()

    def count(self):
        return len(self._items)

    def currentIndex(self):
        return self._index

    def currentText(self):
        return self._items[self._index] if self._items else ""

    def setCurrentIndex(self, i):
        if 0 <= i < len(self._items):
            self._index = i
            self._sync_text()

    def setCurrentText(self, text):
        if text in self._items:
            self._index = self._items.index(text)
            self._sync_text()

    # ---------------------------------------------------------------- 内部
    def _sync_text(self):
        self.text_label.setText(self.currentText() or "请选择")

    def _open(self):
        if not self._items:
            return
        # 已经展开时再点一下 -> 收起
        if self._popup is not None:
            try:
                if self._popup.isVisible():
                    self._popup.close()
                    self._popup = None
                    return
            except RuntimeError:
                self._popup = None
        # 刚被外部点击关掉的话，这一次点击只当作「关闭」，不要又弹开
        if time.monotonic() - self._closed_at < 0.15:
            return
        # 延后一帧再弹出，避免鼠标释放事件立刻把弹层关掉
        QTimer.singleShot(0, self._show_popup)

    def _show_popup(self):
        if not self._items:
            return
        pop = QFrame(None, Qt.Popup | Qt.FramelessWindowHint)
        pop.setObjectName("selectPopup")
        pop.setAttribute(Qt.WA_DeleteOnClose, True)
        pop.setStyleSheet(
            "QFrame#selectPopup{background:#FFFFFF;border:1px solid %s;border-radius:10px;}" % C.BORDER)
        lay = QVBoxLayout(pop)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(2)
        for i, text in enumerate(self._items):
            item = QPushButton(text)
            item.setCursor(Qt.PointingHandCursor)
            item.setMinimumHeight(34)
            item.setStyleSheet(
                "QPushButton{text-align:left;padding:6px 10px;border:none;border-radius:7px;"
                "background:%s;color:%s;font-size:13px;}"
                "QPushButton:hover{background:%s;color:%s;}" % (
                    C.ACCENT_SOFT if i == self._index else "transparent",
                    C.ACCENT if i == self._index else C.TEXT,
                    C.ACCENT_SOFT, C.ACCENT))
            item.clicked.connect(lambda _=False, idx=i, p=pop: self._pick(idx, p))
            lay.addWidget(item)
        pop.setFixedWidth(max(220, self.width()))
        pop.move(self.box.mapToGlobal(QPoint(0, self.box.height() + 6)))
        pop.destroyed.connect(self._on_popup_destroyed)
        self._popup = pop
        pop.show()
        pop.raise_()

    def _on_popup_destroyed(self, *_):
        self._popup = None
        self._closed_at = time.monotonic()

    def _pick(self, idx, pop):
        self._index = idx
        self._sync_text()
        pop.close()
        self._popup = None
        self.changed.emit(idx)


class LogoMark(QLabel):
    """圆角头像 logo，找不到图片时回退成字母块。"""

    def __init__(self, path, size=36, radius=11, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        pm = QPixmap(path)
        if pm.isNull():
            self.setText("C")
            self.setAlignment(Qt.AlignCenter)
            self.setStyleSheet(f"background:{C.ACCENT};color:#FFFFFF;border-radius:{radius}px;"
                               f"font-weight:700;font-size:16px;")
            return
        pm = pm.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        rounded = QPixmap(size, size)
        rounded.fill(Qt.transparent)
        p = QPainter(rounded)
        p.setRenderHint(QPainter.Antialiasing, True)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
        p.setClipPath(clip)
        p.drawPixmap(0, 0, pm)
        p.end()
        self.setPixmap(rounded)


class Chip(QLabel):
    def __init__(self, text="", fg=C.TEXT_2, bg="#F1F2F6", parent=None):
        super().__init__(text, parent)
        self.setObjectName("chip")
        self.set_color(fg, bg)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(22)

    def set_color(self, fg, bg):
        self.setStyleSheet(f"#chip{{color:{fg};background:{bg};border-radius:6px;"
                           f"padding:2px 8px;font-size:11px;font-weight:600;}}")

    def set_state(self, text, fg, bg):
        self.setText(text)
        self.set_color(fg, bg)


def label(text, kind="muted", parent=None):
    lb = QLabel(text, parent)
    if kind:
        lb.setObjectName(kind)
    return lb


def h1(text):
    lb = QLabel(text)
    lb.setObjectName("h1")
    return lb


def h2(text):
    lb = QLabel(text)
    lb.setObjectName("h2")
    return lb


class Segmented(QFrame):
    changed = Signal(str)

    def __init__(self, items, current=None, parent=None):
        super().__init__(parent)
        self.setObjectName("segWrap")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for it in items:
            b = QPushButton(it)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(it == (current or items[0]))
            self._group.addButton(b)
            lay.addWidget(b)
            b.clicked.connect(lambda _=False, v=it: self.changed.emit(v))

    def value(self):
        b = self._group.checkedButton()
        return b.text() if b else ""

    def set_value(self, v):
        for b in self._group.buttons():
            if b.text() == v:
                b.setChecked(True)
                return


class Stat(QWidget):
    """一列统计：标题 / 大数字 / 说明。"""

    def __init__(self, title, value="-", sub="", accent=None, big=False, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.t = label(title, "label")
        self.v = QLabel(value)
        self.v.setObjectName("big" if big else "value")
        self.s = label(sub, "tiny")
        for w in (self.t, self.v, self.s):
            lay.addWidget(w)
        if accent:
            self.v.setStyleSheet(f"color:{accent};")

    def set(self, value=None, sub=None, color=None):
        if value is not None:
            self.v.setText(value)
        if sub is not None:
            self.s.setText(sub)
        if color:
            self.v.setStyleSheet(f"color:{color};")


# ------------------------------------------------------------------ 图表
class Sparkline(QWidget):
    """时间轴折线：最新的点贴在右边，历史向左滚动。"""

    WINDOW_SEC = 7200   # 最多显示最近 2 小时

    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []          # [(ts, value), ...]
        self.setMinimumHeight(150)
        self._color = QColor(C.ACCENT)

    def set_points(self, pts, color=None):
        self.points = list(pts or [])
        if color:
            self._color = QColor(color)
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(4, 10, -4, -8)

        pen = QPen(QColor("#EEF0F4"))
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        for i in range(4):
            y = r.top() + r.height() * i / 3.0
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))

        if len(self.points) < 2:
            return

        pts = [(int(t), float(v)) for t, v in self.points]
        pts.sort(key=lambda x: x[0])
        now = pts[-1][0]
        span = max(1, now - pts[0][0])
        # 窗口贴着数据走：十几秒就能铺满，之后随时间向左滚动
        window = min(float(self.WINDOW_SEC), max(15.0, span * 1.02))

        vals = [v for _, v in pts]
        v_lo, v_hi = min(vals), max(vals)
        lo, hi = v_lo, v_hi
        min_range = max(abs(v_hi) * 0.01, 0.05)   # 太小的波动不该被放大成过山车
        if hi - lo < min_range:
            mid = (hi + lo) / 2
            lo, hi = mid - min_range / 2, mid + min_range / 2
        else:
            pad = (hi - lo) * 0.12
            lo, hi = lo - pad, hi + pad

        def xy(ts, v):
            x = r.right() - (now - ts) / window * r.width()
            y = r.bottom() - (v - lo) / (hi - lo) * r.height()
            return QPointF(max(r.left(), x), y)

        p.setFont(QFont("Microsoft YaHei UI", 8))
        p.setPen(QColor(C.TEXT_3))
        p.drawText(QRectF(r.right() - 110, r.top() - 4, 110, 14),
                   Qt.AlignRight | Qt.AlignTop, f"最高 {v_hi:.2f}")
        p.drawText(QRectF(r.right() - 110, r.bottom() - 14, 110, 14),
                   Qt.AlignRight | Qt.AlignBottom, f"最低 {v_lo:.2f}")

        screen = [xy(t, v) for t, v in pts]
        path = QPainterPath(screen[0])
        for pt in screen[1:]:
            path.lineTo(pt)

        area = QPainterPath(path)
        area.lineTo(screen[-1].x(), r.bottom())
        area.lineTo(screen[0].x(), r.bottom())
        area.closeSubpath()

        grad = QLinearGradient(0, r.top(), 0, r.bottom())
        c1 = QColor(self._color)
        c1.setAlpha(46)
        c2 = QColor(self._color)
        c2.setAlpha(0)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        p.fillPath(area, grad)

        pen = QPen(self._color)
        pen.setWidthF(2.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawPath(path)

        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(screen[-1], 3.2, 3.2)


# ------------------------------------------------------------------ 列表行
# 列宽常量：表头与数据行共用，保证严格对齐
COL_HASH = 118
COL_COIN = 108
COL_NET = 108
COL_CHG = 76
BTN_W = 66


class CoinRow(QFrame):
    clicked = Signal(str)
    action = Signal(str)
    edit = Signal(str)

    def __init__(self, coin, parent=None):
        super().__init__(parent)
        self.coin = coin
        self.setObjectName("row")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(62)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 12, 8)
        lay.setSpacing(10)

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{coin.color};border-radius:4px;")

        self.sym = QLabel(coin.symbol)
        self.sym.setStyleSheet("font-weight:700;font-size:14px;")
        self.sym.setFixedWidth(48)

        self.name = label(coin.name_cn, "tiny")
        left = QHBoxLayout()
        left.setSpacing(8)
        left.addWidget(dot)
        left.addWidget(self.sym)
        left.addWidget(self.name)
        left.addStretch(1)
        lw = QWidget()
        lw.setLayout(left)
        lw.setMinimumWidth(190)
        lay.addWidget(lw, 3)

        self.hash_v = label("-", "mono")
        self.hash_v.setFixedWidth(COL_HASH)
        self.hash_v.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.hash_v)

        self.coin_v = label("-", "mono")
        self.coin_v.setFixedWidth(COL_COIN)
        self.coin_v.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.coin_v)

        self.net_v = QLabel("-")
        self.net_v.setStyleSheet("font-weight:700;font-size:13px;")
        self.net_v.setFixedWidth(COL_NET)
        self.net_v.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.net_v)

        self.chip = Chip("-")
        self.chip.setFixedWidth(COL_CHG)
        lay.addWidget(self.chip)

        if coin.custom:
            self.edit_btn = QPushButton("编辑")
            self.edit_btn.setObjectName("ghost")
            self.edit_btn.setCursor(Qt.PointingHandCursor)
            self.edit_btn.setFixedSize(BTN_W, 30)
            self.edit_btn.clicked.connect(lambda: self.edit.emit(self.coin.symbol))
        else:
            # 占位，保证所有行列宽一致
            self.edit_btn = QWidget()
            self.edit_btn.setFixedSize(BTN_W, 30)
        lay.addWidget(self.edit_btn)

        self.btn = QPushButton("开挖")
        self.btn.setObjectName("ghost")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setFixedSize(BTN_W, 30)
        self.btn.clicked.connect(lambda: self.action.emit(self.coin.symbol))
        lay.addWidget(self.btn)

    def update_values(self, hashrate_txt, coin_day_txt, net_txt, net_val, change_pct):
        self.hash_v.setText(hashrate_txt)
        self.coin_v.setText(coin_day_txt)
        self.net_v.setText(net_txt)
        self.net_v.setStyleSheet(
            f"font-weight:700;font-size:13px;color:{C.GREEN if net_val >= 0 else C.RED};")
        if change_pct is None:
            self.chip.set_state("无数据", C.TEXT_3, "#F1F2F6")
        elif change_pct >= 0:
            self.chip.set_state(f"+{change_pct:.1f}%", C.GREEN, C.GREEN_SOFT)
        else:
            self.chip.set_state(f"{change_pct:.1f}%", C.RED, C.RED_SOFT)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.clicked.emit(self.coin.symbol)
        super().mousePressEvent(ev)


class KV(QWidget):
    """一行键值。"""

    def __init__(self, key, value="-", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.k = label(key, "muted")
        self.v = label(value, "mono")
        self.v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.k)
        lay.addStretch(1)
        lay.addWidget(self.v)

    def set(self, value, color=None):
        self.v.setText(value)
        if color:
            self.v.setStyleSheet(f"color:{color};font-family:{C.MONO};font-size:12px;")
