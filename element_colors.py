"""周期表、组分表和初始靶图共用的显示配色；不参与物理计算。"""
from functools import lru_cache
from matplotlib.colors import LinearSegmentedColormap,to_rgb
from PySide6.QtGui import QColor

# 沿用已有周期表的四组底色；深色端点只用于分数渐变。
COLORS={
    's':('#dcebf9','#2879bd'),
    'p':('#e0f1e2','#278b49'),
    'd':('#fff1c9','#b98008'),
    'f':('#f9e3e8','#bb416a'),
    'unknown':('#e8edf2','#61758b')}

def periodic_family(z):
    if 57<=z<=71 or 89<=z<=103:return 'f'
    if z in {1,3,4,11,12,19,20,37,38,55,56,87,88}:return 's'
    if 21<=z<=30 or 39<=z<=48 or 72<=z<=80:return 'd'
    if 1<=z<=103:return 'p'
    return 'unknown'

def periodic_color(z):return COLORS[periodic_family(z)][0]

@lru_cache(maxsize=1)
def atomic_numbers():
    from element_picker import read_materials
    return {m.symbol:m.z for m in read_materials()}

def species_color(symbol):return periodic_color(atomic_numbers().get(str(symbol),0))

@lru_cache(maxsize=128)
def element_colormap(symbol):
    family=periodic_family(atomic_numbers().get(str(symbol),0));base,deep=COLORS[family]
    # 0 仍保留极淡元素色，与无材料的白色背景区分；0.5 对应周期表底色。
    light=tuple(.96+.04*c for c in to_rgb(base))
    return LinearSegmentedColormap.from_list('element_'+family,[(0,light),(.5,base),(1,deep)],N=256)

def tint_species_item(item,symbol):
    item.setBackground(QColor(species_color(symbol)));item.setForeground(QColor('#24364b'))

def contrast_text(color):
    r,g,b=to_rgb(color)
    return '#18334a' if .2126*r+.7152*g+.0722*b>.58 else 'white'
