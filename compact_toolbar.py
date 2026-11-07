"""紧凑工具栏使用 Qt 原生图标；支持按控件设置悬停提示延迟。"""
from PySide6.QtCore import QSize,Qt
from PySide6.QtWidgets import QApplication,QProxyStyle,QStyle,QToolButton

class OneSecondTooltipStyle(QProxyStyle):
    def styleHint(self,hint,option=None,widget=None,returnData=None):
        if hint==QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            delay=widget.property('tooltipDelayMs') if widget is not None else None
            return int(delay) if delay is not None else 1000
        # 不因刚浏览过另一个按钮而跳过下一次的一秒等待。
        if hint==QStyle.StyleHint.SH_ToolTip_FallAsleepDelay:return 0
        return super().styleHint(hint,option,widget,returnData)

def install_tooltip_delay():
    app=QApplication.instance()
    if not getattr(app,'_one_second_tooltip_style',None):
        style=OneSecondTooltipStyle()
        app.setStyle(style)
        app._one_second_tooltip_style=style

def icon_button(parent,label,icon,slot=None,primary=False):
    button=QToolButton(parent)
    button.setProperty('tooltipDelayMs',500)
    button.setText(label)
    button.setAccessibleName(label)
    button.setToolTip(label)
    button.setStatusTip(label)
    button.setIcon(parent.style().standardIcon(icon))
    button.setIconSize(QSize(20,20))
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    button.setFixedSize(34,32)
    button.setAutoRaise(True)
    if primary:button.setObjectName('primaryTool')
    if slot:button.clicked.connect(slot)
    return button
