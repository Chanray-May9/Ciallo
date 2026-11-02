"""矿工内核管理：下载、解压、启动、日志解析。"""

import os
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile

from .catalog import MINERS

UA = {"User-Agent": "MineDeck/1.0 (+local mining dashboard)"}

HASH_RE = re.compile(r"([\d]+(?:[.,]\d+)?)\s*([KMGTP]?H)\s*/\s*s", re.IGNORECASE)
UNIT = {"H": 1.0, "KH": 1e3, "MH": 1e6, "GH": 1e9, "TH": 1e12, "PH": 1e15}


# ------------------------------------------------------------------ 目录
def miner_root(app_dir):
    p = os.path.join(app_dir, "miners")
    os.makedirs(p, exist_ok=True)
    return p


def find_installed(app_dir, miner_key):
    """在 miners 目录下递归寻找内核 exe。"""
    exe = MINERS[miner_key].exe
    root = miner_root(app_dir)
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.lower() == exe.lower():
                return os.path.join(dirpath, f)
    return None


# ------------------------------------------------------------------ 下载
def _open(url, timeout=30):
    from .net import open_url
    return open_url(url, timeout=timeout)


def _text(url, timeout=20):
    with _open(url, timeout) as r:
        return r.read().decode("utf-8", "ignore"), r.geturl()


def resolve_url(miner_key):
    """优先解析 GitHub 最新稳定版资产，失败则用内置直链。"""
    m = MINERS[miner_key]
    if m.repo:
        try:
            _body, final = _text(f"https://github.com/{m.repo}/releases/latest")
            tag = final.rstrip("/").rsplit("/tag/", 1)[-1]
            page, _ = _text(f"https://github.com/{m.repo}/releases/expanded_assets/{tag}")
            links = re.findall(r'href="(/[^"]+/releases/download/[^"]+)"', page)
            for href in links:
                if m.asset_hint.lower() in href.lower():
                    return "https://github.com" + href, tag
        except Exception:
            pass
    for url in m.direct_urls:
        return url, "内置直链"
    return None, ""


def download(app_dir, miner_key, progress=None, log=None):
    """下载并解压内核，返回 exe 路径。progress(done, total)。"""
    url, ver = resolve_url(miner_key)
    if not url:
        raise RuntimeError("找不到可用下载地址")
    if log:
        log(f"下载 {MINERS[miner_key].name}（{ver}）: {url}")

    root = miner_root(app_dir)
    dl_dir = os.path.join(root, "_downloads")
    os.makedirs(dl_dir, exist_ok=True)
    name = url.split("/")[-1] or "miner.zip"
    zip_path = os.path.join(dl_dir, name)

    with _open(url, timeout=60) as r:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        with open(zip_path, "wb") as f:
            while True:
                chunk = r.read(262144)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)

    target = os.path.join(root, miner_key)
    os.makedirs(target, exist_ok=True)
    if zipfile.is_zipfile(zip_path):
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(target)
    else:  # tar.gz 兜底
        import tarfile
        try:
            with tarfile.open(zip_path) as t:
                t.extractall(target)
        except Exception as exc:
            raise RuntimeError(f"解压失败: {exc}")

    exe = find_installed(app_dir, miner_key)
    if not exe:
        # 有些包把 exe 放在子目录里，再扫一遍
        for dirpath, _d, files in os.walk(target):
            for f in files:
                if f.lower().endswith(".exe") and "miner" in f.lower():
                    return os.path.join(dirpath, f)
        raise RuntimeError("解压完成但内核 exe 不见了，多半被 Windows 安全中心隔离——"
                           "点「修复内核」按提示添加排除项后重新解压")
    if log:
        log(f"已就绪: {exe}")
    return exe


def repair(app_dir, miner_key):
    """用已经下载好的压缩包重新解压，修复 exe 被隔离的情况。"""
    root = miner_root(app_dir)
    dl = os.path.join(root, "_downloads")
    if not os.path.isdir(dl):
        raise RuntimeError("本地没有安装包，请先点「下载内核」")
    target = os.path.join(root, miner_key)
    os.makedirs(target, exist_ok=True)
    found = False
    for name in os.listdir(dl):
        if not name.lower().endswith((".zip", ".tar.gz", ".tgz")):
            continue
        path = os.path.join(dl, name)
        found = True
        try:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path) as z:
                    z.extractall(target)
            else:
                import tarfile
                with tarfile.open(path) as t:
                    t.extractall(target)
        except Exception:
            continue
    if not found:
        raise RuntimeError("本地没有安装包，请先点「下载内核」")
    exe = find_installed(app_dir, miner_key)
    if not exe:
        raise RuntimeError("解压后仍然找不到内核，通常是杀毒软件仍在拦截")
    return exe


def add_defender_exclusion(app_dir):
    """弹 UAC 把内核目录加入 Windows Defender 排除项。"""
    root = miner_root(app_dir)
    cmd = ("Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-Command',"
           f"\"Add-MpPreference -ExclusionPath '{root}'\"")
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                   capture_output=True, text=True, timeout=90,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


# ------------------------------------------------------------------ 日志解析
def parse_hashrate(line):
    """从内核日志中提取算力（H/s）。返回 None 表示该行没有算力。"""
    best = None
    for m in HASH_RE.finditer(line):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        unit = m.group(2).upper()
        best = max(best or 0.0, val * UNIT.get(unit, 1.0))
    return best


SHARE_OK = re.compile(r"(?i)(share accepted|accepted:|accepted share|good share)")
SHARE_BAD = re.compile(r"(?i)(rejected|invalid share|stale share)")


def parse_shares(line):
    ok = 1 if SHARE_OK.search(line) else 0
    bad = 1 if SHARE_BAD.search(line) else 0
    return ok, bad


# ------------------------------------------------------------------ 进程
try:
    from PySide6.QtCore import QObject, QProcess, Signal

    class MinerRunner(QObject):
        line = Signal(str)
        hashrate = Signal(float)
        shares = Signal(int, int)
        state = Signal(str)          # running / stopped / error

        def __init__(self, parent=None):
            super().__init__(parent)
            self.proc = QProcess(self)
            self.proc.setProcessChannelMode(QProcess.MergedChannels)
            self.proc.readyReadStandardOutput.connect(self._read)
            self.proc.finished.connect(self._finished)
            self.proc.errorOccurred.connect(self._error)
            self._buf = ""
            self.accepted = 0
            self.rejected = 0

        # -- public
        def running(self):
            return self.proc.state() != QProcess.NotRunning

        def start(self, exe, args, cwd=None):
            self.accepted = 0
            self.rejected = 0
            if cwd:
                self.proc.setWorkingDirectory(cwd)
            self.proc.start(exe, args)
            if self.proc.waitForStarted(5000):
                self.state.emit("running")
                return True
            self.state.emit("error")
            return False

        def stop(self):
            if self.proc.state() != QProcess.NotRunning:
                self.proc.kill()
                self.proc.waitForFinished(3000)
            self.state.emit("stopped")

        # -- internal
        def _read(self):
            data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "ignore")
            self._buf += data.replace("\r", "\n")
            *lines, self._buf = self._buf.split("\n")
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                self.line.emit(ln)
                h = parse_hashrate(ln)
                if h:
                    self.hashrate.emit(h)
                ok, bad = parse_shares(ln)
                if ok or bad:
                    self.accepted += ok
                    self.rejected += bad
                    self.shares.emit(self.accepted, self.rejected)

        def _finished(self, code, _status):
            self.state.emit("stopped")
            self.line.emit(f"--- 内核退出，代码 {code} ---")

        def _error(self, err):
            self.state.emit("error")
            self.line.emit(f"--- 进程错误: {err} ---")

except Exception:  # 无 Qt 环境时（比如命令行自测）不影响其它模块导入
    MinerRunner = None
