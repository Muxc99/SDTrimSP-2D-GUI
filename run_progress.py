"""Compact run status; only history progress lines count as percentages."""
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressBar


class RunProgress(QProgressBar):
    labels = {
        'ready': ('就绪', 'Ready'), 'starting': ('正在启动', 'Starting'),
        'running': ('运行中', 'Running'), 'finishing': ('正在结束', 'Finishing'),
        'completed': ('运行成功', 'Completed'), 'failed': ('运行失败', 'Failed'),
        'stopping': ('正在停止', 'Stopping'), 'stopped': ('已停止', 'Stopped'),
    }
    pattern = re.compile(r'^\s*ihist:\s*\d+\s+(\d+(?:\.\d+)?)\s*%', re.I)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.language = 'zh'
        self.state = 'ready'
        self.pending = ''
        self.setRange(0, 100)
        self.setValue(0)
        self.setFixedSize(190, 24)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.render()

    def reset_run(self):
        self.pending = ''
        self.setValue(0)
        self.set_state('starting')

    def set_language(self, language):
        self.language = language
        self.render()

    def set_state(self, state):
        self.state = state
        if state == 'completed':
            self.setValue(100)
        self.render()

    def feed(self, text, final=False):
        self.pending += text.replace('\r', '\n')
        lines = self.pending.split('\n')
        self.pending = '' if final else lines.pop()
        for line in lines:
            match = self.pattern.match(line)
            if match:
                self.setValue(max(self.value(), min(100, int(float(match[1])))))
                if self.state in ('starting', 'running', 'finishing'):
                    self.state = 'finishing' if self.value() == 100 else 'running'
        self.render()

    def render(self):
        label = self.labels[self.state][self.language == 'en']
        self.setFormat(label + ' · %p%')
        self.setAccessibleName(label)
        self.setToolTip(label + ('：按内核输出的注量步百分比更新。' if self.language != 'en'
                                 else ': updated from engine history-step progress.'))
        color = {'completed': '#3b9b62', 'failed': '#d75c5c',
                 'stopping': '#dc9c39', 'stopped': '#dc9c39'}.get(self.state, '#57acd0')
        self.setStyleSheet('QProgressBar {border:1px solid #b6c8d8;border-radius:4px;'
                           'background:#eef3f7;color:#18364b;font-size:9pt;}'
                           'QProgressBar::chunk {background:' + color + ';border-radius:3px;}')
