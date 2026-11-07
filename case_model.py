"""SDTrimSP-2D 3.01 输入读写。只更新受支持字段，保留其余文本。"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
import re

LENGTH_KEYS = ('geo_x', 'geo_z', 'geo_dx', 'geo_dz', 'x_start', 'dx_start', 'z_start', 'pr_amp', 'pr_wl')
SCALAR_KEYS = ('flc', 'maxhist', 'ihist_out', 'nr_pproj', 'case_e0', 'case_alpha',
               'case_start', 'case_geo', 'ipot', 'isbv', 'tar_dynamic')
ARRAY_KEYS = ('symbol', 'qu_beam', 'e0_beam', 'alpha0', 'qu_tar', 'qu_max')
REQUIRED = ('ncp',) + LENGTH_KEYS + SCALAR_KEYS + ARRAY_KEYS
ELEMENTS = set(('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn '
                'Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce '
                'Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At '
                'Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr').split())
# 以当前安装的材料表为准，接受 D、T、He3、C_g 等程序自身使用的名称。
_table=Path(__file__).resolve().parents[1]/'work'/'tables'/'table1'
if _table.exists():
    for _line in _table.read_text(encoding='utf-8',errors='replace').splitlines():
        _p=_line.split()
        if len(_p)>=8 and re.fullmatch(r'\d+',_p[1]): ELEMENTS.add(_p[0])

def configure_material_table(path):
    """Use the material table supplied by the selected external engine."""
    global _table
    _table=Path(path).resolve()
    if not _table.exists():return
    for line in _table.read_text(encoding='utf-8',errors='replace').splitlines():
        parts=line.split()
        if len(parts)>=8 and re.fullmatch(r'\d+',parts[1]):ELEMENTS.add(parts[0])

# 经 default_init.F90 核对的默认值；未编辑时不写回这些省略字段。
DEFAULTS={'qu_max':1.,'qu_tar':0.,'e0_beam':0.,'alpha0':0.,'case_e0':0,
          'case_alpha':0,'case_start':3,'tar_dynamic':True,'nr_pproj':10,
          'x_start':0.,'dx_start':0.,'z_start':0.,'geo_x':500.,'geo_z':-500.,
          'geo_dx':50.,'geo_dz':50.,'pr_amp':0.,'pr_wl':1.}
EXTRA_DEFAULTS={'pr_amp':0.,'pr_wl':1.,'iq0':0,'iq0_surf':0,'l_clust':False,
                'l_clust_read':False,'n_clust':1,'loutgas':False,
                'l_two_comp':False,'l_alpha_rough_kor':False,'lmatrices':False}
GEOMETRIES={10:'一维平面',20:'二维平面',24:'轮廓（0～总宽）',25:'轮廓（中心坐标）',
            26:'矩形结构 fig.inp',27:'余弦表面'}

def number(text):
    value = float(str(text).strip().replace('D', 'e').replace('d', 'e'))
    if not math.isfinite(value):
        raise ValueError('数值必须是有限数，不能是 NaN 或无穷大。')
    return value

def fmt(value):
    return format(float(value), '.15g')

def mask(text, strings=False):
    """将注释和可选字符串置空，保留位置；支持 Fortran 双引号转义。"""
    out = list(text)
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if strings and c not in '\r\n':
                out[i] = ' '
            if c == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    if strings: out[i + 1] = ' '
                    i += 2
                    continue
                quote = None
        elif c in "'\"":
            quote = c
            if strings: out[i] = ' '
        elif c == '!':
            while i < len(text) and text[i] not in '\r\n':
                out[i] = ' '
                i += 1
            continue
        i += 1
    return ''.join(out)

def values(raw):
    parts = re.findall(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|[^,\s]+", mask(raw))
    result = []
    for p in parts:
        if p.startswith(('\"', "'")):
            result.append(p[1:-1].replace(p[0]*2, p[0]))
        else:
            repeated = re.fullmatch(r'(\d+)\*(.+)', p)
            count, token = (int(repeated[1]), repeated[2]) if repeated else (1, p)
            if not 0 <= count <= 10000: raise ValueError('数组重复项过大。')
            if token.lower() in ('.true.', '.false.'):
                item = token.lower() == '.true.'
            else:
                item = number(token)
            result.extend([item] * count)
    return result

def same(a, b):
    try: return values(a) == values(b)
    except ValueError: return a.strip() == b.strip()

class Namelist:
    def __init__(self, text):
        self.text = text
        clean = mask(text, strings=True)
        start = re.search(r'&input\b', clean, re.I)
        if not start: raise ValueError('未找到 &INPUT。')
        end = clean.find('/', start.end())
        if end < 0: raise ValueError('未找到 INPUT 的结束符 /。')
        self.end = end
        matches = list(re.finditer(r'\b([A-Za-z][A-Za-z0-9_]*)(\s*\([^=\n]*\))?\s*=', clean[start.end():end]))
        self.fields = {}
        for j, m in enumerate(matches):
            key = m[1].lower()
            if m[2]:
                if key in REQUIRED: raise ValueError(f'{key} 使用了下标赋值；试用版暂不支持表单编辑此写法。')
                continue
            if key in self.fields and key in REQUIRED:
                raise ValueError(f'{key} 重复赋值；请先在原始文件中合并。')
            a = start.end() + m.end()
            b = start.end() + matches[j + 1].start() if j + 1 < len(matches) else end
            segment = mask(text[a:b])
            left = len(segment) - len(segment.lstrip(' \t\r\n,'))
            right = len(segment.rstrip(' \t\r\n,'))
            self.fields[key] = (a + left, a + right)

    def raw(self, key):
        a,b = self.fields[key]
        return self.text[a:b]

    def get(self, key):
        return values(self.raw(key))

    def patch(self, updates, title=None):
        edits = []
        added=[]
        for key, value in updates.items():
            if key in self.fields:
                a,b = self.fields[key]
                if not same(self.text[a:b], value): edits.append((a,b,value))
            else:
                if key in DEFAULTS:
                    default=DEFAULTS[key]
                    if key in ARRAY_KEYS:
                        default_values=[default]*int(self.get('ncp')[0])
                    else: default_values=[default]
                    if values(value)==default_values: continue
                added.append(f'    {key} = {value}')
        if added: edits.append((self.end,self.end,'\n! Added by SDTrimSP-2D input GUI\n'+'\n'.join(added)+'\n'))
        text = self.text
        for a,b,value in sorted(edits, reverse=True): text = text[:a] + value + text[b:]
        if title is not None:
            if '\n' in title or '\r' in title: raise ValueError('标题只能占一行。')
            first = text.find('\n')
            if first >= 0 and text[:first].rstrip('\r') != title:
                text = title + '\n' + text[first+1:]
        return text

@dataclass
class Figure:
    mirror: int
    with_qu: int
    rows: list[list[float]]
    original: str = ''
    baseline: tuple = ()
    tail: str = ''

    @classmethod
    def parse(cls, text, ncp):
        lines = text.splitlines(keepends=True)
        if len(lines) < 5: raise ValueError('fig.inp 少于5行。')
        def integer(line):
            v=number(line.split('!')[0].strip())
            if v != int(v): raise ValueError('fig.inp 控制项必须是整数。')
            return int(v)
        mirror, qu, count = (integer(lines[i]) for i in (2,3,4))
        if mirror not in (0,1) or qu not in (0,1) or not 0 <= count <= 100000:
            raise ValueError('fig.inp 镜像、成分开关或块数不合法。')
        if len(lines) < 5+count: raise ValueError('fig.inp 实际块数少于声明值。')
        rows=[]
        for i in range(count):
            row = [number(v) for v in lines[5+i].split('!')[0].split()]
            if len(row) != 4 + ncp*qu: raise ValueError(f'fig.inp 第{i+6}行列数不匹配。')
            rows.append(row)
        baseline = (mirror,qu,tuple(tuple(r) for r in rows))
        return cls(mirror,qu,rows,text,baseline,''.join(lines[5+count:]))

    def render(self):
        now=(self.mirror,self.with_qu,tuple(tuple(r) for r in self.rows))
        if self.original and now == self.baseline: return self.original
        lines=['# SDTrimSP-2D figure input', '# x1 x2 z1 z2 qu(ncp) [A],[-]',
               f'{self.mirror} ! mirror across x=0', f'{self.with_qu} ! per-block composition', str(len(self.rows))]
        lines += [' '.join(fmt(x) for x in row) for row in self.rows]
        return '\n'.join(lines) + '\n' + self.tail

def read_text(path):
    data=Path(path).read_bytes()
    for encoding in ('utf-8-sig','gb18030'):
        try: return data.decode(encoding)
        except UnicodeDecodeError: pass
    raise ValueError(f'无法解码文件：{path}')

def inspect_input(text):
    n=Namelist(text)
    missing=[k for k in REQUIRED if k not in n.fields and k not in DEFAULTS]
    if missing: raise ValueError('缺少内核要求显式提供的参数：'+', '.join(missing))
    ncp=n.get('ncp')
    if len(ncp)!=1 or ncp[0]!=int(ncp[0]) or not 1<=ncp[0]<=8: raise ValueError('当前内核支持1～8种组分。')
    d={}
    for k in REQUIRED:
        if k in n.fields: d[k]=n.get(k)
        else: d[k]=[DEFAULTS[k]]*(int(ncp[0]) if k in ARRAY_KEYS else 1)
    for k in ('ncp',)+LENGTH_KEYS+SCALAR_KEYS:
        if len(d[k])!=1: raise ValueError(k+' 必须是单值。')
        d[k]=d[k][0]
    for k in ('ncp','maxhist','ihist_out','nr_pproj','case_geo','case_start','case_e0','case_alpha','ipot','isbv'):
        if d[k]!=int(d[k]): raise ValueError(k+' 必须是整数。')
    if d['ncp']!=int(d['ncp']) or not 1<=d['ncp']<=8: raise ValueError('试用版支持1～8种元素。')
    for k in ARRAY_KEYS:
        if len(d[k])!=int(d['ncp']): raise ValueError(k+' 数组长度与 ncp 不一致。')
    for k,v in EXTRA_DEFAULTS.items():
        raw=n.get(k) if k in n.fields else [v]
        if len(raw)!=1: raise ValueError(k+' 必须是单值。')
        d[k]=raw[0]
    d['_defaults']=[k for k in REQUIRED if k not in n.fields]
    return n,d

def validate(d, fig):
    errors=[]; warnings=[]
    for key in ('maxhist','ihist_out','nr_pproj'):
        if d[key]<1 or d[key]!=int(d[key]): errors.append(key+' 必须是正整数。')
    if d['flc']<=0: errors.append('总注量 flc 必须大于0。')
    for key in ('ipot','isbv'):
        if d[key]<1 or d[key]!=int(d[key]): errors.append(key+' 必须为正整数模型编号。')
    if d['ipot'] not in (1,2,3): warnings.append('当前碰撞势编号不在界面说明的1～3中，请核对版本手册。')
    if d['isbv'] in (5,7): errors.append('3.01版不支持 isbv=5 或7。')
    symbols=d['symbol']
    if len(set(symbols))!=len(symbols): errors.append('元素符号不能重复。')
    if any(s not in ELEMENTS for s in symbols): errors.append('材料名未在当前材料表中找到；请核对大小写和别名（支持 D、T、C_g 等）。')
    for key in ('qu_beam','qu_tar','qu_max'):
        if any(v<0 or v>1 for v in d[key]): errors.append(key+' 各分数必须在0～1之间。')
    for key in ('qu_beam','qu_tar'):
        if not math.isclose(sum(d[key]),1,abs_tol=1e-6): errors.append(key+' 原子分数之和必须为1。')
    for i,q in enumerate(d['qu_beam']):
        if q>0 and d['e0_beam'][i]<=0: errors.append(symbols[i]+' 的入射能量必须大于0。')
    if any(abs(v)>180 for v in d['alpha0']): errors.append('入射角绝对值不能大于180°。')
    if d['geo_x']<=0 or d['geo_z']>=0 or d['geo_dx']<=0 or d['geo_dz']<=0:
        errors.append('半宽及网格间距须大于0，geo_z须小于0。')
        return errors,warnings,{}
    mode=int(d['case_geo']); start=int(d['case_start'])
    nx=1 if mode==10 else 2*d['geo_x']/d['geo_dx']; nz=abs(d['geo_z'])/d['geo_dz']
    if mode==10:
        if not math.isclose(2*d['geo_x'],d['geo_dx'],abs_tol=.001): errors.append('一维模式要求 geo_dx=2×geo_x。')
        if start not in (1,3): errors.append('一维模式要求 case_start=1 或3。')
    elif not math.isclose(nx/2,round(nx/2),abs_tol=1e-8): errors.append('geo_x 必须是 geo_dx 的整数倍。')
    if mode not in GEOMETRIES: warnings.append('当前几何模式仅保留参数，不提供完整截面预览，请核对内核支持情况。')
    if not math.isclose(nz,round(nz),abs_tol=1e-8): warnings.append('基底厚度不是 geo_dz 的整数倍，程序会向下扩展到整层。')
    beam=d['geo_dx'] if mode==10 else d['dx_start']
    if start==4 and beam<d['geo_dx']:
        beam=2*d['geo_x']; warnings.append('dx_start 小于网格间距：内核会自动采用整个靶宽，原输入值保持不变。')
    elif beam<d['geo_dx']: errors.append('当前起点模式要求 dx_start 不小于横向网格间距。')
    if beam>2*d['geo_x']+1e-8: errors.append('束斑宽度不能超过靶区总宽。')
    if start==4 and abs(d['x_start'])+beam/2>d['geo_x']+1e-8:
        warnings.append('束斑超出横向边界，程序可能周期映射；请核对是否符合意图。')
    top=0.; occupied={}
    if d['case_geo']==26:
        if fig is None: errors.append('case_geo=26 需要 fig.inp。')
        else:
            for i,r in enumerate(fig.rows,1):
                x1,x2,z1,z2=r[:4]; top=max(top,z2)
                if not (x1<x2 and 0<=z1<z2): errors.append(f'块{i}坐标须满足 x1<x2、0≤z1<z2。')
                if x1 < (-1e-8 if fig.mirror else -d['geo_x']-1e-8) or x2>d['geo_x']+1e-8:
                    errors.append(f'块{i}超出横向范围；镜像模式只填写 x≥0 一侧。')
                if x2-x1>d['geo_dx']+1e-8 or z2-z1>d['geo_dz']+1e-8:
                    errors.append(f'块{i}宽/高超过网格间距，请拆分。')
                if z2/d['geo_dz']>=4999: errors.append(f'块{i}接近竖向索引缓冲区上限，请减小结构高度或核对源码。')
                if fig.with_qu and (len(r)!=4+len(symbols) or any(q<0 or q>1 for q in r[4:]) or not math.isclose(sum(r[4:]),1,abs_tol=1e-6)):
                    errors.append(f'块{i}成分须与元素列数一致，且各项在0～1、合计为1。')
                spans=[(x1,x2)] + ([(-x2,-x1)] if fig.mirror else [])
                for a,b in spans:
                    ix=math.floor(((a+b)/2+d['geo_x'])/d['geo_dx'])
                    iz=math.floor(((z1+z2)/2)/d['geo_dz'])
                    if occupied.get((ix,iz)): errors.append(f'块{i}与块{occupied[ix,iz]}落入同一个基础网格，程序可能拒绝。')
                    occupied[ix,iz]=i
                    if a < -d['geo_x']+ix*d['geo_dx']-1e-8 or b > -d['geo_x']+(ix+1)*d['geo_dx']+1e-8 or z1 < iz*d['geo_dz']-1e-8 or z2 > (iz+1)*d['geo_dz']+1e-8:
                        errors.append(f'块{i}跨越基础网格边界，请沿网格边界拆分。')
    if mode in (24,25,27) and '_files' in d:
        try:
            px,pz=surface_profile(d,d['_files']); top=max(pz)
        except ValueError as exc: errors.append(str(exc))
    if start in (3,4,5,6) and d['z_start']<=top: errors.append('入射起始高度须高于全部表面结构。')
    if start==1: warnings.append('case_start=1：内核从局部表面起射，z_start 不是实际入射高度。')
    if d['case_e0']!=0 or d['case_alpha']!=0:
        warnings.append('非固定能量/角度模式：表中数值是分布参数，图中箭头仅为示意；请在高级参数中核对分布设置。')
    files=d.get('_files')
    if files is not None:
        for key,name in [('iq0','initial_composition.inp'),('iq0_surf','initial_composition_surf.inp')]:
            if d.get(key,0)>0:
                if name not in files: errors.append('启用了 '+key+'，但缺少 '+name)
                else:
                    try: parse_layers(files[name],len(symbols))
                    except ValueError as exc: errors.append(name+'：'+str(exc))
        if d.get('l_clust_read') and 'doped_zellen_2D.inp' not in files: errors.append('团簇读取模式缺少 doped_zellen_2D.inp。')
    if d.get('l_clust'): warnings.append('已启用团簇：参数及附件参与计算；随机团簇位置由内核生成，预览不伪造其位置。')
    if d.get('iq0',0)>0 or d.get('iq0_surf',0)>0: warnings.append('已启用初始分层成分；截面显示连续轮廓/分层示意，内核按网格建靶。')
    if d.get('l_alpha_rough_kor'): warnings.append('已保留局部粗糙入射修正；箭头为参考方向，未逐点绘制局部修正。')
    if d.get('_defaults'): warnings.append('按源码采用省略字段默认值：'+', '.join(d['_defaults'])+'；未编辑时不会补写。')
    cells=round(nx)*math.ceil(nz); histories=d['maxhist']*d['nr_pproj']
    if cells>100000: warnings.append('基础网格超过10万，建议先做小规模试算；本界面未预测内存与运行时长。')
    if beam/d['geo_dx']>0 and histories/(beam/d['geo_dx'])<100:
        warnings.append('平均每列入射抽样少于100，仅为统计量提示；是否充分需检查收敛。')
    if d['ihist_out']>d['maxhist']: warnings.append('输出间隔大于总步数，可能没有中间阶段输出。')
    return list(dict.fromkeys(errors)),warnings,{'nx':round(nx),'nz':math.ceil(nz),'cells':cells,'histories':int(histories),'top':top,'beam_width':beam}

@dataclass
class Profile:
    rows:list[list[float]]
    original:str=''
    baseline:tuple=()
    tail:str=''

    @classmethod
    def parse(cls,text):
        lines=text.splitlines(keepends=True)
        try:
            count=number(lines[1].split('!')[0].strip())
            if count!=int(count) or not 2<=count<=100000: raise ValueError('轮廓点数必须是2～100000的整数。')
            count=int(count); rows=[]
            for line in lines[2:2+count]:
                vals=[number(v) for v in line.split('!')[0].split()]
                if len(vals)!=2: raise ValueError('每个轮廓点须有 x、z 两列。')
                rows.append(vals)
            if len(rows)!=count: raise ValueError('实际轮廓点数少于声明值。')
            if any(rows[i+1][0]<=rows[i][0] for i in range(len(rows)-1)): raise ValueError('轮廓点 x 坐标须严格递增。')
            return cls(rows,text,tuple(map(tuple,rows)),''.join(lines[2+count:]))
        except (IndexError,ValueError) as exc: raise ValueError('rauh.inp：'+str(exc)) from exc

    def render(self):
        if self.original and tuple(map(tuple,self.rows))==self.baseline: return self.original
        return 'surface profile [A]\n'+str(len(self.rows))+'\n'+'\n'.join(' '.join(fmt(v) for v in r) for r in self.rows)+'\n'+self.tail

def surface_profile(d,files):
    import numpy as np
    mode=int(d['case_geo']); half=d['geo_x']
    if mode in (24,25):
        if 'rauh.inp' not in files: raise ValueError('该几何需要 rauh.inp。')
        points=Profile.parse(files['rauh.inp']).rows
        xx=np.array([r[0] for r in points]); zz=np.array([r[1] for r in points])
        if mode==24: xx=xx-half
        if xx[0]>-half+1e-8 or xx[-1]<half-1e-8: raise ValueError('rauh.inp 未覆盖完整靶宽；24模式使用0～总宽，25模式使用中心坐标。')
        samples=np.unique(np.concatenate((np.linspace(-half,half,min(1201,max(101,int(2*half/d['geo_dx'])+1))),xx[(xx>=-half)&(xx<=half)])))
        height=np.interp(samples,xx,zz)
    else:
        samples=np.linspace(-half,half,min(1201,max(101,int(2*half/d['geo_dx'])+1)))
        height=np.zeros_like(samples)
    amp=d.get('pr_amp',0); wl=d.get('pr_wl',1)
    if mode in (24,25,27) and amp>0:
        if wl<=0: raise ValueError('pr_amp>0 时，pr_wl 必须大于0。')
        height += amp*(1-np.cos(2*np.pi*samples/wl))
    return samples,height

def parse_layers(text,ncp):
    lines=text.splitlines()
    try:
        count=int(number(lines[1].split('!')[0]))
        if not 1<=count<=100000: raise ValueError('层数超出范围。')
        upper=number(lines[2].split('!')[0]); rows=[]
        for i in range(count):
            q=[number(v) for v in lines[3+2*i].split('!')[0].split()]
            lower=number(lines[4+2*i].split('!')[0])
            if len(q)!=ncp or any(v<0 or v>1 for v in q) or not math.isclose(sum(q),1,abs_tol=1e-6): raise ValueError('层成分列数、范围或成分和不正确。')
            if lower>=upper: raise ValueError('层坐标必须从上向下严格递减。')
            rows.append((upper,lower,q)); upper=lower
        return rows
    except (IndexError,ValueError) as exc: raise ValueError('分层格式错误：'+str(exc)) from exc
