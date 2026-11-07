"""图形到 fig.inp 的安全转换。坐标统一使用 Å，不改写原始材料密度。"""
import math

MAX_DRAW_CELLS=20000

def grid_key(row,half_width,dx,dz):
    return (math.floor(((row[0]+row[1])/2+half_width)/dx),
            math.floor((row[2]+row[3])/2/dz))

def cell_at(x,z,half_width,dx,dz,mirror=False):
    if dx<=0 or dz<=0 or half_width<=0:raise ValueError('网格间距和横向半宽必须大于零。')
    if z<0 or x<(-1e-9 if mirror else -half_width) or x>=half_width:return None
    ix=math.floor((x+half_width)/dx);iz=math.floor(z/dz)
    if iz>=4998:raise ValueError('绘制高度接近内核竖向索引上限。')
    a=-half_width+ix*dx
    return [max(a,0.) if mirror else a,min(a+dx,half_width),iz*dz,(iz+1)*dz]

def split_rectangle(x1,x2,z1,z2,half_width,dx,dz,mirror=False,fractions=()):
    if dx<=0 or dz<=0 or half_width<=0:raise ValueError('网格间距和横向半宽必须大于零。')
    x1,x2=sorted((x1,x2));z1,z2=sorted((z1,z2))
    x1=max(x1,0. if mirror else -half_width);x2=min(x2,half_width);z1=max(0.,z1)
    if x2-x1<1e-10 or z2-z1<1e-10:return []
    if z2/dz>=4998:raise ValueError('绘制高度接近内核竖向索引上限。')
    ia=math.floor((x1+half_width)/dx);ib=math.ceil((x2+half_width)/dx-1e-12)
    ka=math.floor(z1/dz);kb=math.ceil(z2/dz-1e-12)
    if (ib-ia)*(kb-ka)>MAX_DRAW_CELLS:raise ValueError('单次绘制超过 20000 格，请缩小绘制范围或调整网格。')
    rows=[]
    for iz in range(ka,kb):
        for ix in range(ia,ib):
            a=-half_width+ix*dx;b=a+dx;c=iz*dz;d=c+dz
            rows.append([max(x1,a),min(x2,b),max(z1,c),min(z2,d),*fractions])
    return rows

def ellipse_cells(x1,x2,z1,z2,half_width,dx,dz,mirror=False,fractions=()):
    # 椭圆按格心采样，边界为矩形阶梯近似；不是精确曲线边界。
    x1,x2=sorted((x1,x2));z1,z2=sorted((z1,z2))
    cx=(x1+x2)/2;cz=(z1+z2)/2;rx=(x2-x1)/2;rz=(z2-z1)/2
    if rx<=0 or rz<=0:return []
    candidates=split_rectangle(x1,x2,z1,z2,half_width,dx,dz,mirror,fractions)
    return [r for r in candidates if (((r[0]+r[1])/2-cx)/rx)**2+(((r[2]+r[3])/2-cz)/rz)**2<=1+1e-12]

def merge_rows(existing,new_rows,half_width,dx,dz,overwrite=False):
    """一个背景格只保留一个材料矩形；默认跳过已有格，不破坏其几何。"""
    result=[list(r) for r in existing]
    occupied={grid_key(r,half_width,dx,dz):i for i,r in enumerate(result)}
    skipped=0
    for row in new_rows:
        key=grid_key(row,half_width,dx,dz)
        if key in occupied:
            if overwrite:result[occupied[key]]=list(row)
            else:skipped+=1
        else:
            occupied[key]=len(result);result.append(list(row))
    return result,skipped

def move_rows(rows,selected,shift_x,shift_z,half_width,dx,dz,mirror=False):
    """平移选择项后重新按网格切分；碰到其他材料格则整次操作拒绝。"""
    stationary=[list(r) for i,r in enumerate(rows) if i not in selected]
    moving=[]
    for i in selected:
        r=rows[i];a,b,c,d=r[:4]
        if a+shift_x<(-1e-9 if mirror else -half_width-1e-9) or b+shift_x>half_width+1e-9 or c+shift_z<-1e-9:
            raise ValueError('移动后超出靶区，或进入 z<0 的基底区域。')
        moving.extend(split_rectangle(a+shift_x,b+shift_x,c+shift_z,d+shift_z,half_width,dx,dz,mirror,r[4:]))
    occupied={grid_key(r,half_width,dx,dz) for r in stationary}
    for row in moving:
        key=grid_key(row,half_width,dx,dz)
        if key in occupied:raise ValueError('移动后有多个矩形占用同一网格，请调整位置。')
        occupied.add(key)
    return stationary+moving
