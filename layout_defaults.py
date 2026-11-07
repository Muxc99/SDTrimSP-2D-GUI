"""各页首次显示时应用默认主次比例；后续保留用户拖动的分隔位置。"""
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QSplitter

class DefaultSplitter(QSplitter):
    def __init__(self,orientation,preset,parent=None):
        super().__init__(orientation,parent);self.preset=preset;self.defaults_applied=False
        self.setChildrenCollapsible(False)
    def showEvent(self,event):
        super().showEvent(event)
        if not self.defaults_applied:QTimer.singleShot(0,self.apply_defaults)
    def apply_defaults(self):
        if self.defaults_applied or self.count()!=2:return
        length=(self.width() if self.orientation()==Qt.Orientation.Horizontal else self.height())-self.handleWidth()
        if length<=0:return
        if self.preset=='input':sizes=[round(length*.48),round(length*.52)];stretch=(1,1)
        elif self.preset=='drawing':
            side=round(min(370,max(325,length*.18)));sizes=[max(1,length-side),side];stretch=(1,0)
        elif self.preset=='materials':
            bottom=min(205,round(length*.30));sizes=[max(1,length-bottom),bottom];stretch=(1,0)
        elif self.preset=='results':
            side=round(min(350,max(300,length*.18)));sizes=[side,max(1,length-side)];stretch=(0,1)
        else:raise ValueError('Unknown layout preset: '+self.preset)
        for i,factor in enumerate(stretch):self.setStretchFactor(i,factor)
        self.setSizes(sizes);self.defaults_applied=True
