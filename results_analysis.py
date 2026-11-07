"""Extended SDTrimSP-2D output readers and conservative geometric analysis.
Raw outputs remain unmodified. Optional files are parsed independently.
"""
from pathlib import Path
import re
import math
import numpy as np
import pandas as pd

NUMBER=r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eEdD][+-]?\d+|[+-]\d{3}(?!\d))?"
def fortran_float(value):
    value=value.replace('D','E').replace('d','e')
    if 'e' not in value.lower():value=re.sub(r'(?<=\d)([+-]\d{3})$',r'E\1',value)
    return float(value)

def numbers(line):
    return [fortran_float(v) for v in re.findall(NUMBER,line)]

def finite_frame(rows,columns):
    frame=pd.DataFrame(rows,columns=columns)
    if not frame.empty and not np.isfinite(frame.to_numpy(dtype=float)).all():raise ValueError('Non-finite output values')
    return frame

def header_symbols(text):
    lines=text.splitlines()
    for i,line in enumerate(lines[:-1]):
        if line.lstrip().startswith('# symbol'):return lines[i+1].split()
    return []

def parse_transport(text,kind,symbols):
    lines=text.splitlines();out=[];i=0;n=len(symbols)
    if not n:raise ValueError('Component names are required')
    while i<len(lines):
        if '# geo_nx ihist fluc ncp nr_pproj' not in lines[i]:i+=1;continue
        h=numbers(lines[i].split('#')[0]);i+=1
        if len(h)!=5 or int(h[3])!=n or not 0<int(h[0])<10000000:raise ValueError('Invalid transport block header')
        count=int(h[0]);rows=[]
        while i<len(lines) and len(rows)<count:
            line=lines[i].strip();i+=1
            if not line or line.startswith('#'):continue
            v=numbers(line)
            cols=1+n*(6 if kind=='transport' else 1)
            if len(v)!=cols:raise ValueError('Invalid transport data width')
            rows.append(v)
        if len(rows)!=count:raise ValueError('Truncated transport block')
        groups=['incident','outgoing','incoming','scattered','sputtered','reemitted'] if kind=='transport' else ['redeposit']
        columns=['x_A']+[g+'_'+s for g in groups for s in symbols]
        out.append(dict(history=int(h[1]),fluence=h[2],data=finite_frame(rows,columns)))
    if not out:raise ValueError('No transport blocks')
    return out

def parse_static_transport(text,symbols):
    lines=text.splitlines();out=[];i=0;n=len(symbols)
    if not n:raise ValueError('Component names are required')
    while i<len(lines):
        if '# oberf_nr ihist fluc ncp nr_pproj' not in lines[i]:i+=1;continue
        h=numbers(lines[i].split('#')[0]);i+=1
        if len(h)!=5 or int(h[3])!=n or not 0<int(h[0])<10000000:raise ValueError('Invalid static transport header')
        rows=[]
        while i<len(lines) and len(rows)<int(h[0]):
            line=lines[i].strip();i+=1
            if not line or line.startswith('#'):continue
            v=numbers(line)
            if len(v)!=3+5*n:raise ValueError('Invalid static transport record')
            rows.append(v)
        if len(rows)!=int(h[0]):raise ValueError('Truncated static transport block')
        columns=['x_A','z_A','cell_id']+[g+'_'+s for g in ('incident','outgoing','incoming','scattered','sputtered') for s in symbols]
        out.append(dict(history=int(h[1]),fluence=h[2],data=finite_frame(rows,columns)))
    if not out:raise ValueError('No static surface records')
    return out

def parse_hits(text):
    lines=text.splitlines();x=None;start=None
    for i,line in enumerate(lines):
        if '#   geo_nx' in line and 'xx' in line:
            n=int(numbers(lines[i+1])[0]);x=numbers(lines[i+2])
            if len(x)!=n+1:raise ValueError('Invalid hit-distribution mesh')
        if '#    ihist' in line and 'fluence' in line:start=i+1;break
    if x is None or start is None:raise ValueError('Missing hit distribution header')
    v=[]
    for line in lines[start:]:
        if line.strip() and not line.lstrip().startswith('#'):v.extend(numbers(line))
    size=2+len(x)-1
    if len(v)%size:raise ValueError('Truncated hit distribution')
    out=[]
    for i in range(0,len(v),size):
        out.append(dict(history=int(v[i]),fluence=v[i+1],data=finite_frame(list(zip((np.array(x[:-1])+x[1:])/2,v[i+2:i+size])),['x_A','hits'])))
    if not out:raise ValueError('No hit distribution records')
    return out

SUMMARY_FIELDS=['composition_at_max_height','stopped_inventory','incident','backscattered','back_energy','transmitted','trans_energy','sputtered','sputter_energy','transmitted_recoil','trans_recoil_energy','input_energy','chemical_erosion','reemission']
def parse_summary(text,symbols):
    lines=text.splitlines();rows=[];n=len(symbols)
    if not n:raise ValueError('Component names are required')
    for i,line in enumerate(lines):
        if 'fluc,mindep,maxdep,average' not in line:continue
        h=numbers(line.split('fluc,')[0])
        if len(h)!=4 or i+14>=len(lines):raise ValueError('Truncated global statistics')
        row=dict(fluence_ions_A2=h[0],min_height_A=h[1],max_height_A=h[2],mean_height_A=h[3])
        for j,field in enumerate(SUMMARY_FIELDS):
            vals=numbers(lines[i+1+j].split('cel_qu')[0].split('nproj')[0].split('iback_r')[0].split('ichem')[0].split('reem')[0])
            if len(vals)<n:raise ValueError('Invalid global statistics width')
            for s,v in zip(symbols,vals[:n]):row[field+'_'+s]=v
        rows.append(row)
    if not rows:raise ValueError('No global statistics blocks')
    return pd.DataFrame(rows)

def parse_energy(text):
    group='';rows=[]
    for line in text.splitlines():
        if 'ENERGY ANALYSE' in line:group=line.strip().rstrip(':');continue
        m=re.match(r'\s*(NUCL\.LOSS|ELECT\.LOSS|E_BACK|E_TRAN|E_STOP|E_SBE|E_TOT|E_INPUT)\s*:\s*('+NUMBER+r')\s+keV',line)
        if m:rows.append((group,m[1],fortran_float(m[2])))
    if not rows:raise ValueError('No signed energy budget')
    return pd.DataFrame(rows,columns=['group','term','energy_keV'])

def parse_timing(text):
    rows=[]
    for line in text.splitlines():
        m=re.match(r'\s*time for ([^:]+):\s*('+NUMBER+r')\s+s',line)
        if m:rows.append((m[1].strip(),fortran_float(m[2])))
    if not rows:raise ValueError('No timing summary')
    return pd.DataFrame(rows,columns=['stage','seconds'])

PARTICLE_COLUMNS=['species_id','generation_collisions','fluence_ions_A2','energy_eV','x_start_A','y_start_A','z_start_A','x_end_A','y_end_A','z_end_A','x_max_A','y_max_A','z_max_A','cos_polar','cos_azimuth','path_A','elastic_loss_eV','transfer_loss_eV','electronic_loss_eV','damage','time']
def parse_particles(text):
    lines=text.splitlines();start=next((i for i,s in enumerate(lines) if 'species' in s and 'gen/coll' in s),None)
    if start is None:
        if re.search(r'\b0\s+number particle from SDTrimSP',text):return finite_frame([],PARTICLE_COLUMNS)
        raise ValueError('Missing particle header')
    rows=[]
    for line in lines[start+1:]:
        if line.strip().lstrip('#').strip()=='ende':break
        if not line.strip() or line.lstrip().startswith('#'):continue
        v=numbers(line)
        if len(v)!=len(PARTICLE_COLUMNS):raise ValueError('Truncated or unsupported particle record')
        rows.append(v)
    return finite_frame(rows,PARTICLE_COLUMNS)

def parse_trajectories(text):
    lines=text.splitlines();out=[];i=0
    while i<len(lines):
        if not ('i_traj' in lines[i] and 'termflag' in lines[i]):i+=1;continue
        if i+2>=len(lines):raise ValueError('Truncated trajectory header')
        h=numbers(lines[i+1]);i+=3
        if len(h)!=8 or not 0<=int(h[6])<10000000:raise ValueError('Invalid trajectory metadata')
        rows=[]
        for k in range(int(h[6])):
            if i>=len(lines):raise ValueError('Truncated trajectory')
            v=numbers(lines[i]);i+=1
            if len(v)!=6:raise ValueError('Invalid trajectory point')
            rows.append(v)
        if rows:out.append(dict(trajectory=int(h[0]),history=int(h[1]),projectile=int(h[2]),parent=int(h[3]),species_id=int(h[5]),termination=int(h[7]),data=finite_frame(rows,['point','x_A','y_A','z_A','time','energy_eV'])))
    return out

def parse_profiles(text,symbols):
    out=[];lines=text.splitlines();i=0;n=len(symbols)
    while i<len(lines):
        if '#Nr-cell' not in lines[i]:i+=1;continue
        h=numbers(lines[i].split('#')[0]);i+=1
        if len(h)!=5:raise ValueError('Invalid profile header')
        if i>=len(lines):raise ValueError('Missing profile coordinate')
        upper=numbers(lines[i]);i+=1;rows=[]
        if len(upper)!=1:raise ValueError('Invalid profile depth')
        while i<len(lines) and '#Nr-cell' not in lines[i]:
            if not lines[i].strip():i+=1;continue
            q=numbers(lines[i]);i+=1
            if i>=len(lines) or '#Nr-cell' in lines[i]:raise ValueError('Truncated profile interval')
            lower=numbers(lines[i]);i+=1
            if len(q)!=n or len(lower)!=1:raise ValueError('Invalid profile interval')
            rows.append([upper[0],lower[0]]+q);upper=lower
        if rows:out.append(dict(cell_id=int(h[0]),x1_A=h[1],x2_A=h[2],data=finite_frame(rows,['z1_nominal_A','z2_nominal_A']+['fraction_'+s for s in symbols])))
    if not out:raise ValueError('No nominal profiles')
    return out

def parse_active(text,symbols):
    out=[];lines=text.splitlines();i=0;n=len(symbols)
    while i<len(lines):
        if 'ihist' not in lines[i] or '# maxhist' in lines[i]:i+=1;continue
        h=numbers(lines[i].split('ihist')[0]);i+=1
        if len(h)!=1:continue
        if i>=len(lines):raise ValueError('Missing active-cell block')
        v=numbers(lines[i]);i+=1
        if len(v)!=n+2:raise ValueError('Invalid active-cell header')
        count=int(v[0]);rows=[];ended=False
        while i<len(lines):
            v=numbers(lines[i]);i+=1
            if len(v)!=n+2:raise ValueError('Invalid active-cell record')
            if int(v[0])==count+1:ended=True;break
            rows.append(v)
        if not ended:raise ValueError('Truncated active-cell block')
        out.append(dict(history=int(h[0]),fluence=float('nan'),data=finite_frame(rows,['cell_id']+['delta_'+s for s in symbols]+['volume_statistic'])))
    if not out:raise ValueError('No active-cell records')
    return out

def horizontal_profile(snapshot,symbol,x_A=None):
    df=snapshot['data'];projected_width=df.x2_A.max()-df.x1_A.min();df=df[df.density_at_A3>0]
    if df.empty:raise ValueError('No material in this snapshot')
    if x_A is not None:
        selected=df[(df.x1_A<=x_A)&(df.x2_A>x_A)]
        if selected.empty and np.isclose(x_A,df.x2_A.max()):selected=df[(df.x1_A<x_A)&(df.x2_A>=x_A)]
        if selected.empty:raise ValueError('No material at this x coordinate')
        selected=selected.sort_values('z1_A');top=selected.z2_A.max()
        return pd.DataFrame(dict(z1_A=selected.z1_A,z2_A=selected.z2_A,depth1_A=top-selected.z2_A,depth2_A=top-selected.z1_A,fraction=selected['fraction_'+symbol],density_at_A3=selected['fraction_'+symbol]*selected.density_at_A3))
    edges=np.unique(df[['z1_A','z2_A']].to_numpy());rows=[];width=projected_width
    for a,b in zip(edges[:-1],edges[1:]):
        cut=df[(df.z1_A<b)&(df.z2_A>a)];dx=(cut.x2_A-cut.x1_A).to_numpy();density=cut.density_at_A3.to_numpy();q=cut['fraction_'+symbol].to_numpy()
        all_atoms=float(np.sum(dx*density));atoms=float(np.sum(dx*density*q))
        rows.append((a,b,atoms/all_atoms if all_atoms>0 else np.nan,atoms/width,float(np.sum(dx))/width))
    return pd.DataFrame(rows,columns=['z1_A','z2_A','fraction','density_at_A3','material_width_fraction'])

def cross_section(snapshot,symbol,z_A):
    df=snapshot['data'];cut=df[(df.z1_A<=z_A)&(df.z2_A>z_A)&(df.density_at_A3>0)].sort_values('x1_A')
    if cut.empty:raise ValueError('No material at this z coordinate')
    return pd.DataFrame(dict(x1_A=cut.x1_A,x2_A=cut.x2_A,fraction=cut['fraction_'+symbol],density_at_A3=cut['fraction_'+symbol]*cut.density_at_A3))

def projected_inventory(snapshots,symbols):
    rows=[]
    for snap in snapshots:
        df=snap['data'];width=df.x2_A.max()-df.x1_A.min()
        if width<=0:raise ValueError('Invalid projected width')
        area=(df.x2_A-df.x1_A)*(df.z2_A-df.z1_A)
        row=dict(history=snap['history'],fluence_ions_A2=snap['fluence'])
        for s in symbols:row[s]=float((df['fraction_'+s]*df.density_at_A3*area).sum()/width)
        rows.append(row)
    return pd.DataFrame(rows)

def envelope(snapshot,xmin=None,xmax=None):
    df=snapshot['data'];df=df[df.density_at_A3>0]
    lo=df.x1_A.min() if xmin is None else xmin;hi=df.x2_A.max() if xmax is None else xmax
    if not lo<hi:raise ValueError('x minimum must be less than x maximum')
    edges=np.unique(np.clip(np.r_[df.x1_A,df.x2_A,lo,hi],lo,hi));rows=[]
    for a,b in zip(edges[:-1],edges[1:]):
        cut=df[(df.x1_A<b)&(df.x2_A>a)]
        rows.append((a,b,cut.z2_A.max() if not cut.empty else np.nan))
    return pd.DataFrame(rows,columns=['x1_A','x2_A','height_A'])

def morphology(snapshots,reference_A=0.,xmin=None,xmax=None):
    rows=[]
    for snap in snapshots:
        top=envelope(snap,xmin,xmax);valid=top.dropna();dx=valid.x2_A-valid.x1_A
        if valid.empty:continue
        df=snap['data'];lo=top.x1_A.min();hi=top.x2_A.max();width=np.maximum(0,np.minimum(df.x2_A,hi)-np.maximum(df.x1_A,lo));height=np.maximum(0,df.z2_A-np.maximum(df.z1_A,reference_A))
        row=dict(history=snap['history'],fluence_ions_A2=snap['fluence'],max_height_A=valid.height_A.max(),min_height_A=valid.height_A.min(),mean_height_A=float((valid.height_A*dx).sum()/dx.sum()),height_above_reference_A=max(0,valid.height_A.max()-reference_A),occupied_width_above_reference_A=float(dx[valid.height_A>reference_A+1e-9].sum()),area_above_reference_A2=float((width*height*(df.density_at_A3>0)).sum()),material_area_A2=float((width*(df.z2_A-df.z1_A)*(df.density_at_A3>0)).sum()))
        rows.append(row)
    result=pd.DataFrame(rows)
    if result.empty:raise ValueError('No material in the chosen x range')
    result['material_area_change_A2']=result.material_area_A2-result.material_area_A2.iloc[0]
    return result

def surface_change(first,last,xmin=None,xmax=None):
    a=envelope(first,xmin,xmax);b=envelope(last,xmin,xmax);edges=np.unique(np.r_[a.x1_A,a.x2_A,b.x1_A,b.x2_A]);rows=[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        mid=(lo+hi)/2;va=a[(a.x1_A<=mid)&(a.x2_A>mid)];vb=b[(b.x1_A<=mid)&(b.x2_A>mid)]
        za=va.height_A.iloc[0] if len(va) else np.nan;zb=vb.height_A.iloc[0] if len(vb) else np.nan
        rows.append((lo,hi,za,zb,zb-za))
    return pd.DataFrame(rows,columns=['x1_A','x2_A','initial_height_A','current_height_A','change_A'])

OPTIONAL_NAMES=['loss_depos.dat','loss_depos_2.dat','re_deposit.dat','surf_proj.dat','E0_31_3D.dat','profil.dat','energy_analyse.dat','time00.dat','activ_cell.dat']
def extend_dataset(result,contents):
    result.setdefault('warnings',[]);result.setdefault('particles',{});result.setdefault('trajectories',{})
    if not result['symbols']:
        for text in contents.values():
            sy=header_symbols(text)
            if sy:result['symbols']=sy;break
    sy=result['symbols']
    parsers={'loss_depos.dat':('transport',lambda t:parse_transport(t,'transport',sy)),'loss_depos_2.dat':('transport_static',lambda t:parse_static_transport(t,sy)),'re_deposit.dat':('redeposit',lambda t:parse_transport(t,'redeposit',sy)),'surf_proj.dat':('hits',parse_hits),'E0_31_3D.dat':('statistics',lambda t:parse_summary(t,sy)),'profil.dat':('profiles',lambda t:parse_profiles(t,sy)),'energy_analyse.dat':('energy',parse_energy),'time00.dat':('timing',parse_timing),'activ_cell.dat':('active',lambda t:parse_active(t,sy))}
    for name,text in contents.items():
        try:
            own_symbols=header_symbols(text)
            if own_symbols and sy and own_symbols!=sy:raise ValueError('Component order does not match other loaded files')
            if name in parsers:
                key,parser=parsers[name];result[key]=parser(text)
            elif name.startswith('partic_') and name.endswith('.dat'):
                result['particles'][name]=parse_particles(text);key='particles:'+name
            elif name.startswith('trajec_') and name.endswith('.dat'):
                result['trajectories'][name]=parse_trajectories(text);key='trajectories:'+name
            else:continue
            result['files'][key]=name
        except (ValueError,IndexError,KeyError) as error:
            result['warnings'].append(name+': '+str(error))
    result['ignored']=[n for n in contents if n not in result['files'].values()]
    # Active-cell outputs do not contain fluence. Match only exact history metadata.
    known={s['history']:s['fluence'] for s in result.get('cells',[])}
    for snap in result.get('active',[]):snap['fluence']=known.get(snap['history'],float('nan'))
    return result

