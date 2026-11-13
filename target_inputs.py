"""GUI-owned target tools and auxiliary formats. No engine data is bundled here."""
import math
import re
import numpy as np
from case_model import number,fmt,parse_layers,surface_profile,Profile

LOCAL_FILE='doped_zellen_2D.inp'
CLUSTER_COUNTS=(1,4,9,16,25,36)

def compound_catalog():
    """Read names/constituents from the user's external table only."""
    import case_model
    from pathlib import Path
    if not case_model._table:return None
    path=Path(case_model._table).parent/'table.compound'
    if not path.is_file():return {}
    rows={}
    for line in path.read_text(encoding='utf-8',errors='replace').splitlines()[8:]:
        parts=line.split()
        if len(parts)>=11 and not line.lstrip().startswith(('#','!')):rows[parts[0]]=parts[1:3]
    return rows

def grid_shape(d):
    return (1 if d['case_geo']==10 else round(2*d['geo_x']/d['geo_dx']),
            math.ceil(abs(d['geo_z'])/d['geo_dz']-1e-10))

def fractions(q,n):
    if len(q)!=n or any(not math.isfinite(v) or v<0 or v>1 for v in q) or not math.isclose(sum(q),1,abs_tol=1e-6):
        raise ValueError('成分列须与元素对应，分数在 0–1 且合计为 1。 / Fractions must match species, lie in 0–1 and sum to 1.')

def parse_local(text,d):
    lines=text.splitlines();nx,nz=grid_shape(d);n=len(d['symbol'])
    try:
        header=[number(v) for v in lines[1].split('!')[0].split()]
        if len(header)!=3 or any(v!=int(v) for v in header):raise ValueError('count nx nz must be integers')
        count,x,z=map(int,header)
        if not 0<=count<=1000000 or (x,z)!=(nx,nz):raise ValueError('网格维度不匹配 / Grid dimensions do not match')
        rows={}
        if len(lines)<count+2:raise ValueError('缺少单元行 / Missing cell rows')
        for line in lines[2:2+count]:
            v=[number(s) for s in line.split('!')[0].split()]
            if len(v)!=n+2 or any(t!=int(t) for t in v[:2]):raise ValueError('ix iz q1 ... qN')
            ix,iz=map(int,v[:2]);q=v[2:];fractions(q,n)
            if not 1<=ix<=nx or not -5000<=iz<=nz+4999:raise ValueError('单元索引越界 / Cell index out of range')
            if (ix,iz) in rows:raise ValueError('重复单元 / Duplicate cell')
            rows[ix,iz]=q
        return rows
    except (IndexError,ValueError) as e:raise ValueError(LOCAL_FILE+': '+str(e)) from e

def render_local(rows,d):
    nx,nz=grid_shape(d)
    text='Doped cells: ix iz atomic fractions\n'+f'{len(rows)} {nx} {nz}\n'
    text+=''.join(f'{ix} {iz} '+' '.join(fmt(v) for v in q)+'\n' for (ix,iz),q in sorted(rows.items()))
    parse_local(text,d);return text

def parse_distribution(text,angle=False):
    rows=[]
    for line in text.splitlines()[1:]:
        line=line.split('!')[0].strip()
        if not line:continue
        v=[number(s) for s in line.replace(',',' ').split()]
        if len(v)!=2:raise ValueError('分布需两列：数值 权重（不含点数行）。 / Use two columns: value weight (no count line).')
        x,w=v
        if w<0 or x<0 or (not angle and x<=0) or (angle and x>90):raise ValueError('分布数值或权重越界 / Distribution value or weight out of range')
        if rows and x<=rows[-1][0]:raise ValueError('分布横坐标须严格递增 / Distribution values must increase')
        rows.append(v)
    if len(rows)>(90 if angle else 100):raise ValueError('超过本机 3.01 的分布点数上限 / Distribution exceeds 3.01 point limit: '+str(90 if angle else 100))
    if len(rows)<2 or not any(q[1]>0 for q in rows):raise ValueError('至少两点且权重不能全零 / Need two points with positive total weight')
    return rows

def atomic_numbers(symbols):
    from element_picker import read_materials
    import case_model
    materials=read_materials(case_model._table) if case_model._table else []
    lookup={m.symbol:m.z for m in materials}
    periodic='H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr'.split()
    lookup.update({s:i+1 for i,s in enumerate(periodic)});lookup.update(D=1,T=1)
    try:return [int(lookup[s]) for s in symbols]
    except KeyError as e:raise ValueError('请配置材料表以确定原子序数 / Configure a material table for atomic numbers: '+str(e))

def parse_matrix(text,symbols):
    lines=text.splitlines();n=len(symbols)
    try:
        if number(lines[1])!=n:raise ValueError('ncp mismatch')
        if [number(v) for v in lines[2:2+n]]!=atomic_numbers(symbols):raise ValueError('元素次序不匹配 / Species order mismatch')
        matrix=[[number(v) for v in line.split('!')[0].split()] for line in lines[3+n:3+2*n]]
        if len(matrix)!=n or any(len(r)!=n or any(v<0 for v in r) for r in matrix):raise ValueError('需要非负 ncp×ncp 矩阵 / Need a nonnegative ncp x ncp matrix')
        return matrix
    except (IndexError,ValueError) as e:raise ValueError('mat_surfb.inp: '+str(e)) from e

def render_matrix(matrix,symbols):
    text='Surface binding matrix [eV]\n'+str(len(symbols))+'\n'+'\n'.join(map(str,atomic_numbers(symbols)))+'\nMatrix\n'
    text+='\n'.join(' '.join(fmt(v) for v in r) for r in matrix)+'\n'
    parse_matrix(text,symbols);return text

def template(name,d):
    if name=='energy.inp':
        e=max([v for v in d['e0_beam'] if v>0] or [1000.])
        return 'Energy [eV], relative weight\n'+f'{fmt(e*.9)} 1\n{fmt(e*1.1)} 1\n'
    if name=='angle.inp':return 'Polar angle [deg], relative weight\n0 1\n45 1\n90 0\n'
    if name==LOCAL_FILE:return render_local({},d)
    if name=='mat_surfb.inp':
        # Explicit editable starting values; never presented as material constants.
        return render_matrix([[1. for _ in d['symbol']] for _ in d['symbol']],d['symbol'])
    raise ValueError('此文件没有模板，请导入已有输入。 / No template; import an existing input: '+name)

def validate_auxiliary(d):
    errors=[];warnings=[];files=d.get('_files',{})
    active=[]
    if d['case_e0']==1:active.append(('energy.inp',lambda t:parse_distribution(t)))
    if d['case_alpha']==4:active.append(('angle.inp',lambda t:parse_distribution(t,True)))
    if d['isbv']==6:active.append(('mat_surfb.inp',lambda t:parse_matrix(t,d['symbol'])))
    if d.get('l_clust') and d.get('l_clust_read'):active.append((LOCAL_FILE,lambda t:parse_local(t,d)))
    for name,parser in active:
        try:
            if name not in files:raise ValueError('缺少文件 / Missing file')
            parser(files[name])
        except ValueError as e:errors.append(name+': '+str(e))
    if d.get('l_clust') and not d.get('l_clust_read'):
        if d.get('n_clust') not in CLUSTER_COUNTS:errors.append('n_clust: 1, 4, 9, 16, 25, 36 only')
        try:fractions(d.get('qu_clust',[]),len(d['symbol']))
        except ValueError as e:errors.append('qu_clust: '+str(e))
    if d.get('geo_imax',1) not in (1,2):errors.append('geo_imax: 1 or 2 only')
    if d.get('iq0_surf',0) not in (0,1):errors.append('iq0_surf: 本机只执行 0 / 1 分支 / This kernel implements only 0 / 1')
    flags=[d.get('l_two_comp'+suffix,False) for suffix in ('','2','3')]
    if sum(bool(v) for v in flags)>1:errors.append('化合物模型开关互斥 / Compound model flags are mutually exclusive')
    count=next((i+1 for i,v in enumerate(flags) if v),0)
    if len(d['symbol'])+2*count>8:errors.append('化合物内部展开后超过 8 组分 / Compound expansion exceeds 8 components')
    if count:
        # tableread expands ncp before qu_init, sbv_init and geometry-file reads.
        # These editors intentionally use the explicit case species, not hidden
        # compound components. Do not emit shorter rows that Fortran can misread.
        dependent=d.get('iq0',0)>0 or d.get('iq0_surf',0)>0 or d.get('l_clust') or d['isbv']==6
        if d['case_geo']==26 and 'fig.inp' in files:
            from case_model import Figure
            try:dependent|=bool(Figure.parse(files['fig.inp'],len(d['symbol'])).with_qu)
            except ValueError:pass
        if dependent:errors.append('化合物会展开内部组分；当前按元素列编辑的分层、局部、团簇、逐块成分或矩阵不能与其混用。 / Compound expansion requires extra component columns; these composition-file editors cannot be combined with it.')
    for i in range(count):
        suffix='' if i==0 else str(i+1);formula=d.get('two_comp'+suffix,'')
        tokens=re.findall(r'([A-Z][a-z]?)(\d*)',formula)
        if len(formula)>10 or len(tokens)!=2 or ''.join(s+v for s,v in tokens)!=formula or any(s not in d['symbol'] or (v and int(v)==0) for s,v in tokens):
            errors.append('two_comp'+suffix+': 请选择已列出的两种元素组成的化合物 / Formula must contain two listed elements')
        catalog=compound_catalog()
        if catalog is not None and formula not in catalog:errors.append('two_comp'+suffix+': 外部 table.compound 未找到 / Not found in external table.compound: '+formula)
        density=d.get('rhom'+suffix,-1)
        if density!=-1 and density<=0:errors.append('rhom'+suffix+': use -1 (table) or a positive density')
    density=d.get('dns_0',[-1]*len(d['symbol']))
    if len(density)!=len(d['symbol']) or any(v!=-1 and v<=0 for v in density):errors.append('dns_0: 每元素正原子数密度或 -1 / Positive atomic density per species or -1')
    for key,name in [('iq0','initial_composition.inp'),('iq0_surf','initial_composition_surf.inp')]:
        if d.get(key,0)>0 and name in files:
            try:
                rows=parse_layers(files[name],len(d['symbol']))
                thin=[str(i+1) for i,(u,l,q) in enumerate(rows) if u-l<d['geo_dz']-1e-8]
                if thin:warnings.append(name+': 薄于 geo_dz 的层 / Layers thinner than geo_dz: '+', '.join(thin))
                if key=='iq0_surf' and rows[0][0]>0:errors.append(name+': 表面偏移须 ≤0 / Surface offsets must be <=0')
            except ValueError:pass # Main layer validator reports syntax errors.
    if d['case_geo'] in (24,25):
        try:
            p=Profile.parse(files['rauh.inp']);sx,sz=surface_profile(d,files)
            if not math.isclose(sz[0],sz[-1],abs_tol=1e-7):warnings.append('周期边界两端高度不一致 / Profile endpoints have different heights at the periodic seam')
            if min(v[1] for v in p.rows)<=d['geo_z']:errors.append('轮廓触及或穿过基底底部 / Profile reaches or crosses substrate bottom')
        except (KeyError,ValueError):pass
    if d['case_geo']==28:warnings.append('几何 28 为专用圆柱截面：半径由内核硬编码（2510/25010 Å），仅保留已有输入；无通用圆柱编辑。 / Geometry 28 is specialized; radius is hardcoded (2510/25010 A). Existing inputs only.')
    return errors,warnings

def composition_field(d,fig,X,Z,idx):
    """Continuous schematic, honoring init order; not a replica of cut-cell geometry."""
    sx,sz=surface_profile(d,d['_files']);surf=np.interp(X,sx,sz)
    solid=(Z>=d['geo_z'])&(Z<=surf)
    values=np.full(X.shape,float(d['qu_tar'][idx]))
    if d.get('iq0',0)>0:
        for u,l,q in parse_layers(d['_files']['initial_composition.inp'],len(d['symbol'])):values=np.where((Z>=l)&(Z<u),q[idx],values)
    # fig blocks are initialized AFTER qu_init; bulk layers do not repaint them.
    if fig:
        regular=X.ndim==2 and np.all(X==X[0:1,:]) and np.all(Z==Z[:,0:1])
        for row in fig.rows:
            x1,x2,z1,z2=row[:4]
            spans=[(x1,x2)]+([(-x2,-x1)] if fig.mirror else [])
            for a,b in spans:
                if regular:
                    left,right=np.searchsorted(X[0],[a,b]);bottom,top=np.searchsorted(Z[:,0],[z1,z2])
                    solid[bottom:top,left:right]=True
                    surf[:,left:right]=np.maximum(surf[:,left:right],z2)
                    values[bottom:top,left:right]=row[4+idx] if fig.with_qu else d['qu_tar'][idx]
                else:
                    inside=(X>=a)&(X<b)&(Z>=z1)&(Z<z2)
                    solid|=inside;surf=np.where((X>=a)&(X<b),np.maximum(surf,z2),surf)
                    values=np.where(inside,row[4+idx] if fig.with_qu else d['qu_tar'][idx],values)
    if d.get('iq0_surf',0)==1:
        for u,l,q in parse_layers(d['_files']['initial_composition_surf.inp'],len(d['symbol'])):
            values=np.where((Z-surf>l)&(Z-surf<=u),q[idx],values)
    if d.get('l_clust') and d.get('l_clust_read'):
        nx,nz=grid_shape(d)
        ix=np.floor((X+nx*d['geo_dx']/2)/d['geo_dx']).astype(int)+1
        iz=np.floor(Z/d['geo_dz']+nz).astype(int)+1
        rows=parse_local(d['_files'][LOCAL_FILE],d)
        # Sparse lookup avoids rows x preview-pixels work on densely painted targets.
        lookup={x+(z+5000)*(nx+1):q[idx] for (x,z),q in rows.items()}
        flat=(ix+(iz+5000)*(nx+1)).ravel()
        overrides=np.fromiter((lookup.get(int(k),np.nan) for k in flat),dtype=float,count=flat.size).reshape(X.shape)
        values=np.where(np.isfinite(overrides),overrides,values)
    return np.ma.masked_where(~solid,values)

def composition_mesh(d,fig=None):
    """Use physical grid lines, retaining explicit block boundaries at normal scale.

    Bounded overview decimation skips whole grid intervals; it never shifts their
    origin or stretches the grid to fit the current structure height.
    """
    nx,nz=grid_shape(d);dx,dz=d['geo_dx'],d['geo_dz']
    sx,sz=surface_profile(d,d['_files'])
    top=max(0.,float(max(sz)),max((r[3] for r in fig.rows),default=0.) if fig else 0.)
    bottom=min(d['geo_z'],-nz*dz);low=math.floor(bottom/dz);high=math.ceil(top/dz)
    xs=max(1,math.ceil(nx/1000));zs=max(1,math.ceil((high-low)/1000))
    xx=np.r_[np.arange(0,nx,xs)*dx-d['geo_x'],d['geo_x']]
    zz=np.r_[np.arange(low,high,zs)*dz,high*dz,bottom,d['geo_z'],0.,top]
    if fig and fig.rows:
        bounds=np.asarray(fig.rows)[:,:4]
        xe=np.unique(bounds[:,:2]);ze=np.unique(bounds[:,2:])
        if fig.mirror:xe=np.unique(np.r_[xe,-xe])
        if len(xe)<=1000:xx=np.r_[xx,xe]
        if len(ze)<=1000:zz=np.r_[zz,ze]
    if d.get('iq0',0)>0:
        layers=parse_layers(d['_files']['initial_composition.inp'],len(d['symbol']))
        edges=np.unique([edge for u,l,q in layers for edge in (u,l) if bottom<edge<top])
        if len(edges)<=1000:zz=np.r_[zz,edges]
    return np.unique(xx),np.unique(zz)

def profile_from_columns(text,d,factor=1.):
    rows=[]
    for line in text.splitlines():
        line=line.split('#')[0].split('!')[0].strip()
        if not line:continue
        v=[number(s)*factor for s in re.split(r'[,;\s]+',line)]
        if len(v)!=2:raise ValueError('需要 x z 两列 / Two columns x z required')
        rows.append(v)
    if len(rows)<2:raise ValueError('至少两个点 / At least two points')
    # Editor always uses centered physical x; file 24 uses distance from left.
    p=Profile([[x+(d['geo_x'] if d['case_geo']==24 else 0),z] for x,z in rows])
    Profile.parse(p.render());test=dict(d,_files={**d['_files'],'rauh.inp':p.render()});surface_profile(test,test['_files'])
    if min(z for _,z in rows)<=d['geo_z']:raise ValueError('轮廓不得穿过底部 / Profile must stay above bottom')
    return p.render()

def cylinder_schematic(d):
    """Bounded sampling of 3.01 geometry-28 corner selection (not a mesh export)."""
    radius=2510. if d['geo_x']<3000 else 25010.
    nx,nz=grid_shape(d);dx,dz=d['geo_dx'],d['geo_dz']
    # Source scans i=1..nx-1 and k=-5000..nz+4999 (last x column excluded).
    xx=np.linspace(-nx*dx/2,nx*dx/2,min(601,max(2,nx+1)))
    zz=np.linspace(max(-radius,(-5001-nz)*dz),min(radius,4999*dz),min(601,max(2,int(2*radius/dz)+1)))
    X,Z=np.meshgrid((xx[1:]+xx[:-1])/2,(zz[1:]+zz[:-1])/2)
    ix=np.floor((X+nx*dx/2)/dx).astype(int)+1;iz=np.floor(Z/dz+nz).astype(int)+1
    x0=(ix-1)*dx-nx*dx/2;z0=(iz-1-nz)*dz
    far_x=np.maximum(abs(x0),abs(x0+dx));far_z=np.maximum(abs(z0),abs(z0+dz))
    solid=(far_x**2+far_z**2<=radius**2)&(ix<nx)&(iz>=-5000)&(iz<=nz+4999)
    return xx,zz,solid,radius
