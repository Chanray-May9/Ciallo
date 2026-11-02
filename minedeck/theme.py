"""MineDeck 主题：浅色、极简、现代（Linear / Vercel 风格）。"""


class C:
    BG = "#F4F5F7"
    SURFACE = "#FFFFFF"
    SURFACE_2 = "#FAFBFC"
    BORDER = "#E8EAEF"
    BORDER_2 = "#D9DDE5"
    TEXT = "#12141A"
    TEXT_2 = "#5B6270"
    TEXT_3 = "#8C93A2"
    ACCENT = "#4F46E5"
    ACCENT_HOVER = "#4338CA"
    ACCENT_SOFT = "#EEF0FE"
    GREEN = "#0E9F6E"
    GREEN_SOFT = "#E7F6F0"
    RED = "#D93036"
    RED_SOFT = "#FDECEC"
    AMBER = "#B45309"
    AMBER_SOFT = "#FDF3E3"
    MONO = '"Cascadia Mono","JetBrains Mono","Consolas",monospace'
    SANS = '"Microsoft YaHei UI","Segoe UI","PingFang SC",sans-serif'


_QSS = """
* { outline: none; }
QWidget { color: @TEXT@; font-family: @SANS@; font-size: 14px; }
QMainWindow, #root { background: @BG@; }
QToolTip { background: #1F2430; color: #FFFFFF; border: none; padding: 6px 9px; border-radius: 6px; font-size: 12px; }

#sidebar { background: @SURFACE@; border-right: 1px solid @BORDER@; }
#brandTitle { font-size: 16px; font-weight: 700; color: @TEXT@; }
#brandSub { font-size: 12px; color: @TEXT_3@; }
#navBtn { text-align: left; padding: 9px 12px; border-radius: 9px; color: @TEXT_2@;
          font-size: 14px; border: 1px solid transparent; background: transparent; }
#navBtn:hover { background: #F1F2F6; color: @TEXT@; }
#navBtn:checked { background: @ACCENT_SOFT@; color: @ACCENT@; font-weight: 600; border: 1px solid #E0E3FF; }

#card { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 14px; }
#cardSoft { background: @SURFACE_2@; border: 1px solid @BORDER@; border-radius: 12px; }
#h1 { font-size: 22px; font-weight: 700; }
#h2 { font-size: 16px; font-weight: 600; }
#label { font-size: 13px; color: @TEXT_3@; }
#muted { font-size: 13px; color: @TEXT_2@; }
#tiny { font-size: 12px; color: @TEXT_3@; }
#big { font-size: 34px; font-weight: 700; }
#value { font-size: 19px; font-weight: 600; }
#mono { font-family: @MONO@; font-size: 13px; }
#monoBig { font-family: @MONO@; font-size: 26px; font-weight: 600; }

QPushButton#primary { background: @ACCENT@; color: #FFFFFF; border: none; border-radius: 10px;
                      padding: 11px 20px; font-weight: 600; font-size: 13px; }
QPushButton#primary:hover { background: @ACCENT_HOVER@; }
QPushButton#primary:pressed { background: #3730A3; }
QPushButton#primary:disabled { background: #C8CAF0; color: #FFFFFF; }

QPushButton#ghost { background: @SURFACE@; border: 1px solid @BORDER_2@; border-radius: 9px;
                    padding: 8px 14px; color: @TEXT@; font-size: 13px; }
QPushButton#ghost:hover { background: #F3F4F7; }
QPushButton#ghost:disabled { color: @TEXT_3@; border-color: @BORDER@; }

QPushButton#danger { background: @SURFACE@; border: 1px solid #F2C7C7; color: @RED@;
                     border-radius: 9px; padding: 8px 14px; font-size: 13px; }
QPushButton#danger:hover { background: @RED_SOFT@; }

QPushButton#seg { padding: 5px 13px; border-radius: 7px; border: none; background: transparent;
                  color: @TEXT_2@; font-size: 12px; }
QPushButton#seg:hover { color: @TEXT@; }
QPushButton#seg:checked { background: @SURFACE@; color: @TEXT@; font-weight: 600; border: 1px solid @BORDER@; }
#segWrap { background: #ECEEF3; border-radius: 9px; }

QPushButton#link { border: none; background: transparent; color: @ACCENT@; font-size: 12px; padding: 2px; }
QPushButton#link:hover { color: @ACCENT_HOVER@; text-decoration: underline; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: @SURFACE@; border: 1px solid @BORDER_2@; border-radius: 9px; padding: 9px 12px;
    selection-background-color: @ACCENT_SOFT@; selection-color: @TEXT@; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid @ACCENT@; }
QLineEdit[invalid="true"] { border: 1px solid @RED@; background: @RED_SOFT@; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { border: 1px solid @BORDER@; border-radius: 8px; background: @SURFACE@;
    selection-background-color: @ACCENT_SOFT@; selection-color: @TEXT@; padding: 4px; outline: none; }
QSpinBox::up-button, QDoubleSpinBox::up-button { width: 16px; border: none; }
QSpinBox::down-button, QDoubleSpinBox::down-button { width: 16px; border: none; }

QPlainTextEdit { background: @SURFACE_2@; border: 1px solid @BORDER@; border-radius: 10px;
    font-family: @MONO@; font-size: 11px; color: #3B4250; padding: 8px; }

QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #D6DAE3; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #C1C6D2; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

#row { background: @SURFACE@; border-radius: 10px; }
#row:hover { background: #F7F8FA; }
#divider { background: @BORDER@; }
#chip { border-radius: 6px; padding: 3px 8px; font-size: 12px; font-weight: 600; }
#dot { border-radius: 4px; }

QSlider::groove:horizontal { height: 4px; background: #E4E7EE; border-radius: 2px; }
QSlider::sub-page:horizontal { background: @ACCENT@; border-radius: 2px; }
QSlider::add-page:horizontal { background: #E4E7EE; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; height: 14px; margin: -6px 0; background: #FFFFFF;
    border: 2px solid @ACCENT@; border-radius: 8px; }
QSlider::handle:horizontal:hover { border-color: @ACCENT_HOVER@; }

#select { background: @SURFACE@; border: 1px solid @BORDER_2@; border-radius: 9px; }
#select:hover { border-color: #B4BAC8; background: #FCFCFD; }
#selectPopup { background: @SURFACE@; border: 1px solid @BORDER@; border-radius: 10px; }
"""

QSS = (_QSS.replace("@SANS@", C.SANS).replace("@MONO@", C.MONO)
           .replace("@BG@", C.BG).replace("@SURFACE_2@", C.SURFACE_2)
           .replace("@SURFACE@", C.SURFACE).replace("@BORDER_2@", C.BORDER_2)
           .replace("@BORDER@", C.BORDER).replace("@TEXT_3@", C.TEXT_3)
           .replace("@TEXT_2@", C.TEXT_2).replace("@TEXT@", C.TEXT)
           .replace("@ACCENT_SOFT@", C.ACCENT_SOFT).replace("@ACCENT_HOVER@", C.ACCENT_HOVER)
           .replace("@ACCENT@", C.ACCENT).replace("@GREEN@", C.GREEN)
           .replace("@RED_SOFT@", C.RED_SOFT).replace("@RED@", C.RED)
           .replace("@AMBER@", C.AMBER))

