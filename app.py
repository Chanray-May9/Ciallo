"""MineDeck 启动入口。

用法：
    python app.py            正常启动
    python app.py --shot     无界面渲染截图（自检用）
"""

import os
import shutil
import sys

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QAbstractSpinBox, QComboBox, QSlider

from minedeck.assets import asset_path
from minedeck.context import AppContext
from minedeck.theme import QSS
from minedeck.ui.main import MainWindow


class WheelGuard(QObject):
    """避免鼠标滚轮扫过控件时误改数值/选项（获得焦点后才允许滚轮调节）。"""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel:
            if isinstance(obj, (QAbstractSpinBox, QComboBox, QSlider)) and not obj.hasFocus():
                ev.ignore()
                return True
        return False

APP_DIR = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
           else os.path.dirname(os.path.abspath(__file__)))


def _data_dir():
    """配置与内核放在固定的用户目录，换版本 / 挪动 exe 都不用重下内核。"""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "Ciallo")
    os.makedirs(path, exist_ok=True)
    # 从旧版本（exe 同目录 data/、miners/）迁移一次
    old_data = os.path.join(APP_DIR, "data")
    old_miners = os.path.join(APP_DIR, "miners")
    new_data = os.path.join(path, "data")
    new_miners = os.path.join(path, "miners")
    try:
        if os.path.isdir(old_data) and not os.path.exists(os.path.join(new_data, "config.json")):
            shutil.copytree(old_data, new_data, dirs_exist_ok=True)
        if os.path.isdir(old_miners) and not os.path.isdir(new_miners):
            shutil.copytree(old_miners, new_miners, dirs_exist_ok=True)
    except Exception:
        pass
    return path


DATA_DIR = _data_dir()


def build_app():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Ciallo")
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    app.setStyleSheet(QSS)

    # 任务栏 / 标题栏图标
    icon_path = asset_path("logo.ico")
    if not os.path.exists(icon_path):
        icon_path = asset_path("logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    try:  # 让任务栏按自己的图标分组，而不是归到 python.exe
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Ciallo.Miner.1")
    except Exception:
        pass

    app._wheel_guard = WheelGuard(app)
    app.installEventFilter(app._wheel_guard)
    return app


def main():
    app = build_app()
    ctx = AppContext(DATA_DIR)
    win = MainWindow(ctx)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
