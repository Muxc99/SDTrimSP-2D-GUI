"""Plan species changes before touching widgets; never reinterpret unknown arrays."""
from case_model import Namelist,values,fmt,parse_layers,ARRAY_KEYS,LENGTH_KEYS,SCALAR_KEYS
from layer_editor import render_layers
from target_inputs import parse_local,render_local,parse_matrix,render_matrix

def plan_species_change(owner,operation,index=None,symbol=None):
    old=[owner.cell(owner.species,i,0) for i in range(owner.species.rowCount())]
    count=len(old);extra=owner.extra_updates();nl=Namelist(owner.namelist.patch(extra))
    updates={};files={};known={'qu_clust':0.,'dns_0':-1.}
    if operation=='remove':
        # Removing a used species would alter mass fractions and irradiation.
        for j in (1,4):
            if float(owner.cell(owner.species,index,j))!=0:
                raise ValueError('该元素仍用于束流或基底，先将其分数调整为零。 / Species is used by beam or substrate; set its fraction to zero first.')
        if owner.with_qu.isChecked():
            for r in range(owner.blocks.rowCount()):
                if float(owner.cell(owner.blocks,r,4+index))!=0:raise ValueError('凸起仍含此元素 / Protrusions still contain this species')
    excluded=set(ARRAY_KEYS+LENGTH_KEYS+SCALAR_KEYS+('ncp','tttt'))
    for key in nl.fields:
        if key in excluded:continue
        array=nl.get(key)
        if key not in known:
            positional={'e_surfb','e_displ','e_cutoff','e_bulkb','isot','charge','beta0','z0_rel','inel0','ioutput_part','ioutput_hist','diff','diff0','qu_dif','qu_out','qu_set'}
            if len(array)>1 or key in positional:
                raise ValueError('扩展数组须先在输入文本中同步，未改变元素： / Synchronize this advanced array in input text first: '+key)
            continue
        if len(array)!=count:raise ValueError(key+': 元素列数不匹配 / Species count mismatch')
        new=list(array)
        if operation=='add':new.append(known[key])
        elif operation=='remove':
            if key=='qu_clust' and new[index]!=0:raise ValueError('团簇仍含此元素 / Clusters still contain this species')
            del new[index]
        elif operation=='replace' and key=='dns_0':new[index]=-1.
        updates[key]=', '.join(map(fmt,new))
    # Indexed assignments need explicit human interpretation, not a guessed remap.
    import re
    from case_model import mask
    if re.search(r'\b\w+\s*\([^=\n]*\)\s*=',mask(nl.text,strings=True)):
        raise ValueError('存在下标赋值，请在文本中同步元素依赖。 / Indexed assignments require explicit text updates.')
    if any(nl.get(k)[0] for k in ('l_two_comp','l_two_comp2','l_two_comp3') if k in nl.fields):
        raise ValueError('请先关闭化合物模型再改变元素。 / Disable the compound model before changing species.')
    new_symbols=list(old)
    if operation=='add':new_symbols.append('')
    elif operation=='remove':del new_symbols[index]
    else:new_symbols[index]=symbol
    def remap(q):
        q=list(q)
        if operation=='add':q.append(0.)
        elif operation=='remove':
            if q[index]!=0:raise ValueError('辅助成分文件仍含此元素 / An auxiliary composition still contains this species')
            del q[index]
        return q
    # Use the old grid and species count even when there is a pending blank row.
    _,d=__import__('case_model').inspect_input(nl.text);d['symbol']=old;d['ncp']=count
    source=owner.current_files()
    for name in ('initial_composition.inp','initial_composition_surf.inp'):
        if name in source:files[name]=render_layers([(u,l,remap(q)) for u,l,q in parse_layers(source[name],count)],len(new_symbols))
    name='doped_zellen_2D.inp'
    if name in source:
        rows=parse_local(source[name],d);candidate=dict(d,symbol=new_symbols)
        files[name]=render_local({key:remap(q) for key,q in rows.items()},candidate)
    if 'mat_surfb.inp' in source:
        if operation in ('add','replace'):raise ValueError('请先移除或手动重建结合能矩阵，再添加 / 替换元素。 / Remove or rebuild the binding matrix before adding / replacing species.')
        m=parse_matrix(source['mat_surfb.inp'],old);m.pop(index)
        for r in m:r.pop(index)
        files['mat_surfb.inp']=render_matrix(m,new_symbols)
    return updates,files

def commit_species_plan(owner,plan):
    updates,files=plan;owner.set_extra_values(updates)
    for name,text in files.items():owner.set_auxiliary_file(name,text)
