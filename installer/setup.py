"""Ciallo 一键安装包（内置主程序，双击即装）。

用法：
    CialloSetup.exe               图形界面安装 / 卸载
    CialloSetup.exe --install-silent   静默安装（测试用）
    CialloSetup.exe --uninstall-silent 静默卸载
"""

import os
import subprocess
import sys

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

APP_NAME = "Ciallo～(∠・ω< )⌒☆"
SHORT_NAME = "Ciallo"
TARGET_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), SHORT_NAME)
TARGET_EXE = os.path.join(TARGET_DIR, "Ciallo.exe")
START_MENU = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu",
                          "Programs", "Ciallo.lnk")
DESKTOP_LNK = os.path.join(os.path.expanduser("~"), "Desktop", "Ciallo.lnk")
UNINSTALL_BAT = os.path.join(TARGET_DIR, "uninstall.bat")
REG_PATH = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Ciallo"


def base_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def payload():
    return os.path.join(base_dir(), "payload", "Ciallo.exe")


def icon_path():
    p = os.path.join(base_dir(), "assets", "logo.ico")
    return p if os.path.exists(p) else ""


def run_ps(script):
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True, text=True, timeout=60,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        pass


def make_shortcut(path, target):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    run_ps(f'$s=(New-Object -ComObject WScript.Shell).CreateShortcut("{path}");'
           f'$s.TargetPath="{target}";$s.WorkingDirectory="{TARGET_DIR}";'
           f'$s.IconLocation="{target},0";$s.Description="{APP_NAME}";$s.Save()')


def write_uninstaller():
    bat = f"""@echo off
chcp 65001 >nul
taskkill /f /im Ciallo.exe >nul 2>&1
del "{DESKTOP_LNK}" >nul 2>&1
del "{START_MENU}" >nul 2>&1
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Ciallo" /f >nul 2>&1
ping -n 2 127.0.0.1 >nul
rd /s /q "{TARGET_DIR}" >nul 2>&1
exit
"""
    with open(UNINSTALL_BAT, "w", encoding="utf-8") as f:
        f.write(bat)


def register_uninstall():
    run_ps(
        f'New-Item -Path "{REG_PATH}" -Force | Out-Null;'
        f'Set-ItemProperty -Path "{REG_PATH}" -Name DisplayName -Value "{APP_NAME}";'
        f'Set-ItemProperty -Path "{REG_PATH}" -Name DisplayVersion -Value "1.0.0";'
        f'Set-ItemProperty -Path "{REG_PATH}" -Name Publisher -Value "Ciallo";'
        f'Set-ItemProperty -Path "{REG_PATH}" -Name DisplayIcon -Value "{TARGET_EXE}";'
        f'Set-ItemProperty -Path "{REG_PATH}" -Name InstallLocation -Value "{TARGET_DIR}";'
        f'Set-ItemProperty -Path "{REG_PATH}" -Name UninstallString -Value \'cmd /c ""{UNINSTALL_BAT}""\';'
        f'Set-ItemProperty -Path "{REG_PATH}" -Name NoModify -Value 1 -Type DWord;'
        f'Set-ItemProperty -Path "{REG_PATH}" -Name NoRepair -Value 1 -Type DWord')


def install(progress=None):
    src = payload()
    if not os.path.exists(src):
        raise RuntimeError("安装包里缺少主程序")
    os.makedirs(TARGET_DIR, exist_ok=True)
    total = os.path.getsize(src)
    done = 0
    with open(src, "rb") as f, open(TARGET_EXE, "wb") as out:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress:
                progress(done / total)
    make_shortcut(DESKTOP_LNK, TARGET_EXE)
    make_shortcut(START_MENU, TARGET_EXE)
    write_uninstaller()
    register_uninstall()
    return TARGET_EXE


def uninstall():
    run_ps(f'Get-Process Ciallo -ErrorAction SilentlyContinue | Stop-Process -Force')
    for p in (DESKTOP_LNK, START_MENU):
        try:
            os.remove(p)
        except OSError:
            pass
    run_ps(f'Remove-Item -Path "{REG_PATH}" -Recurse -Force -ErrorAction SilentlyContinue')
    run_ps(f'Start-Process cmd -ArgumentList \'/c ping -n 2 127.0.0.1 >nul & rd /s /q "{TARGET_DIR}"\' '
           f'-WindowStyle Hidden')


def main():
    args = sys.argv[1:]
    if "--install-silent" in args:
        print(install())
        return
    if "--uninstall-silent" in args:
        uninstall()
        print("uninstalled")
        return

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMessageBox,
                                   QProgressBar, QPushButton, QVBoxLayout, QWidget)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if icon_path():
        app.setWindowIcon(QIcon(icon_path()))

    win = QWidget()
    win.setWindowTitle(f"{APP_NAME} 安装程序")
    win.setFixedSize(560, 300)
    win.setStyleSheet("""
        QWidget { background: #F4F5F7; color: #12141A; font-family: "Microsoft YaHei UI"; }
        #card { background: #FFFFFF; border: 1px solid #E8EAEF; border-radius: 14px; }
        QLabel#title { font-size: 20px; font-weight: 700; }
        QLabel#sub { color: #5B6270; font-size: 13px; }
        QLabel#path { color: #8C93A2; font-size: 12px; }
        QPushButton#primary { background: #4F46E5; color: #FFF; border: none; border-radius: 10px;
                              padding: 11px 22px; font-weight: 600; font-size: 14px; }
        QPushButton#primary:hover { background: #4338CA; }
        QPushButton#ghost { background: #FFF; border: 1px solid #D9DDE5; border-radius: 9px;
                            padding: 9px 16px; font-size: 13px; }
        QPushButton#ghost:hover { background: #F3F4F7; }
        QProgressBar { border: none; background: #ECEEF3; border-radius: 6px; height: 10px;
                       text-align: center; color: transparent; }
        QProgressBar::chunk { background: #4F46E5; border-radius: 6px; }
    """)

    outer = QVBoxLayout(win)
    outer.setContentsMargins(18, 18, 18, 18)
    card = QWidget()
    card.setObjectName("card")
    outer.addWidget(card)

    lay = QVBoxLayout(card)
    lay.setContentsMargins(24, 22, 24, 20)
    lay.setSpacing(10)

    head = QHBoxLayout()
    head.setSpacing(14)
    logo_file = os.path.join(base_dir(), "assets", "logo.png")
    if os.path.exists(logo_file):
        pic = QLabel()
        pm = QPixmap(logo_file).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pic.setPixmap(pm)
        head.addWidget(pic)
    texts = QVBoxLayout()
    texts.setSpacing(2)
    t = QLabel(APP_NAME)
    t.setObjectName("title")
    s = QLabel("显卡挖矿工作台 · 一键安装")
    s.setObjectName("sub")
    texts.addWidget(t)
    texts.addWidget(s)
    head.addLayout(texts)
    head.addStretch(1)
    lay.addLayout(head)

    path_label = QLabel(f"安装位置：{TARGET_DIR}")
    path_label.setObjectName("path")
    path_label.setWordWrap(True)
    lay.addWidget(path_label)
    lay.addSpacing(4)

    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(0)
    lay.addWidget(bar)

    status = QLabel("准备就绪")
    status.setObjectName("sub")
    lay.addWidget(status)
    lay.addStretch(1)

    btns = QHBoxLayout()
    btns.addStretch(1)
    b_un = QPushButton("卸载已安装版本")
    b_un.setObjectName("ghost")
    b_open = QPushButton("打开程序")
    b_open.setObjectName("ghost")
    b_install = QPushButton("一键安装")
    b_install.setObjectName("primary")
    btns.addWidget(b_un)
    btns.addWidget(b_open)
    btns.addWidget(b_install)
    lay.addLayout(btns)

    installed = os.path.exists(TARGET_EXE)
    if installed:
        status.setText("已检测到安装，可再次安装覆盖")

    def do_install():
        b_install.setEnabled(False)
        status.setText("正在复制主程序…")
        try:
            install(progress=lambda p: (bar.setValue(int(p * 100)), app.processEvents()))
            bar.setValue(100)
            status.setText("安装完成，已创建桌面和开始菜单快捷方式")
            QMessageBox.information(win, "安装完成",
                                    f"已安装到：\n{TARGET_DIR}\n\n桌面和开始菜单已有快捷方式。")
            subprocess.Popen([TARGET_EXE], close_fds=True)
        except Exception as exc:
            status.setText(f"安装失败：{exc}")
            QMessageBox.critical(win, "安装失败", str(exc))
        finally:
            b_install.setEnabled(True)

    def do_uninstall():
        if QMessageBox.question(win, "卸载", "确定卸载并删除程序文件吗？\n挖矿配置和内核会一起删除。",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            uninstall()
            status.setText("已卸载")
            bar.setValue(0)

    b_install.clicked.connect(do_install)
    b_un.clicked.connect(do_uninstall)
    b_open.clicked.connect(lambda: os.path.exists(TARGET_EXE) and subprocess.Popen([TARGET_EXE]))

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
