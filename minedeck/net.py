"""网络工具：统一的代理感知 opener（GUI 程序常常要读 Windows 代理设置）。"""

import os
import sys
import urllib.request

UA = {"User-Agent": "MineDeck/1.0 (+local mining dashboard)"}
_OPENER = None


def system_proxies():
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


def opener():
    global _OPENER
    if _OPENER is None:
        _OPENER = urllib.request.build_opener(
            urllib.request.ProxyHandler(system_proxies()))
    return _OPENER


def open_url(url, timeout=20):
    req = url if isinstance(url, urllib.request.Request) else urllib.request.Request(url, headers=UA)
    return opener().open(req, timeout=timeout)
