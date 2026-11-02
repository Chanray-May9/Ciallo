"""静态资源定位（源码运行与单文件 exe 都能找到 assets）。"""

import os
import sys

APP_NAME = "Ciallo～(∠・ω< )⌒☆"


def asset_path(name):
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", name)
