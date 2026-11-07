"""Batch target display: exact grid pixels plus vector geometry for partial cells.

This module only creates display artists. Input rows, order and compositions stay intact.
"""
import numpy as np
from matplotlib.collections import PolyCollection,LineCollection
from matplotlib.colors import Normalize,ListedColormap


class CellEdges(LineCollection):
    """Avoid subpixel mesh strokes obscuring the composition when zoomed out."""
    def __init__(self,segments,dx,dz,**kwargs):
        super().__init__(segments,**kwargs);self.cell_size=(dx,dz)

    def draw(self,renderer):
        transform=self.axes.transData
        origin=transform.transform((0,0));size=np.abs(transform.transform(self.cell_size)-origin)
        if min(size)>=3:super().draw(renderer)


def _runs(mask):
    changes=np.flatnonzero(np.diff(np.r_[False,mask,False]))
    return changes.reshape(-1,2)


def grid_segments(filled,x0,z0,gx,dx,dz,factor):
    height,width=filled.shape;segments=[]
    horizontal=np.zeros((height+1,width),dtype=bool)
    horizontal[:-1]|=filled;horizontal[1:]|=filled
    vertical=np.zeros((height,width+1),dtype=bool)
    vertical[:,:-1]|=filled;vertical[:,1:]|=filled
    for j,mask in enumerate(horizontal):
        z=(z0+j)*dz/factor
        for start,stop in _runs(mask):
            segments.append([((-gx+(x0+start)*dx)/factor,z),((-gx+(x0+stop)*dx)/factor,z)])
    for i,mask in enumerate(vertical.T):
        x=(-gx+(x0+i)*dx)/factor
        for start,stop in _runs(mask):segments.append([(x,(z0+start)*dz/factor),(x,(z0+stop)*dz/factor)])
    return segments


def selection_rectangles(ax,bounds,grid,factor,facecolor,edgecolor,alpha,linewidth,zorder):
    """A selection can cover many cells without creating one artist per cell."""
    if not bounds:return []
    bounds=np.asarray(bounds,dtype=float);gx,dx,dz=grid
    ix=np.floor(((bounds[:,0]+bounds[:,1])*.5+gx)/dx).astype(np.int64)
    iz=np.floor((bounds[:,2]+bounds[:,3])*.5/dz).astype(np.int64)
    expected=np.column_stack((-gx+ix*dx,-gx+(ix+1)*dx,iz*dz,(iz+1)*dz))
    width=int(ix.max()-ix.min()+1);height=int(iz.max()-iz.min()+1)
    if len(bounds)>=128 and width*height<=2_000_000 and np.all(np.isclose(bounds,expected,rtol=0,atol=1e-8)):
        x0=int(ix.min());z0=int(iz.min());filled=np.zeros((height,width),dtype=bool)
        filled[iz-z0,ix-x0]=True;artists=[]
        if facecolor!='none':
            extent=((-gx+x0*dx)/factor,(-gx+(x0+width)*dx)/factor,z0*dz/factor,(z0+height)*dz/factor)
            artists.append(ax.imshow(np.ma.masked_where(~filled,filled),origin='lower',extent=extent,
                           cmap=ListedColormap([facecolor]),vmin=0,vmax=1,alpha=alpha,
                           interpolation='nearest',aspect='auto',zorder=zorder))
        edges=CellEdges(grid_segments(filled,x0,z0,gx,dx,dz,factor),dx/factor,dz/factor,
                        colors=edgecolor,alpha=alpha,linewidths=linewidth,zorder=zorder)
        ax.add_collection(edges,autolim=False);artists.append(edges)
        return artists
    vertices=bounds[:,[0,2,1,2,1,3,0,3]].reshape(-1,4,2)/factor
    artist=PolyCollection(vertices,facecolors=facecolor,edgecolors=edgecolor,alpha=alpha,
                          linewidths=linewidth,zorder=zorder)
    ax.add_collection(artist,autolim=False);return [artist]


def add_target_blocks(ax,fig,data,index,factor,cmap):
    if not fig.rows:return
    rows=np.asarray(fig.rows,dtype=float)
    values=rows[:,4+index] if fig.with_qu else np.full(len(rows),data['qu_tar'][index])
    bounds=rows[:,:4]
    if fig.mirror:
        reflected=bounds[:,[1,0,2,3]]*np.array([-1,-1,1,1])
        # Interleave to retain the old paint order even for invalid overlapping inputs.
        bounds=np.stack((bounds,reflected),axis=1).reshape(-1,4)
        values=np.repeat(values,2)
    gx,dx,dz=data['geo_x'],data['geo_dx'],data['geo_dz']
    ix=np.floor(((bounds[:,0]+bounds[:,1])*.5+gx)/dx).astype(np.int64)
    iz=np.floor((bounds[:,2]+bounds[:,3])*.5/dz).astype(np.int64)
    expected=np.column_stack((-gx+ix*dx,-gx+(ix+1)*dx,iz*dz,(iz+1)*dz))
    regular=np.all(np.isclose(bounds,expected,rtol=0,atol=1e-8),axis=1)
    width=int(ix.max()-ix.min()+1);height=int(iz.max()-iz.min()+1)
    # Bound allocation for sparse structures and imported files with extreme extents.
    unique=len(set(zip(ix,iz)))==len(bounds)
    use_pixels=len(bounds)>=128 and width*height<=2_000_000 and unique
    if use_pixels and regular.any():
        x0=int(ix.min());z0=int(iz.min())
        image=np.full((height,width),np.nan)
        image[iz[regular]-z0,ix[regular]-x0]=values[regular]
        extent=((-gx+x0*dx)/factor,(-gx+(x0+width)*dx)/factor,z0*dz/factor,(z0+height)*dz/factor)
        artist=ax.imshow(np.ma.masked_invalid(image),origin='lower',extent=extent,cmap=cmap,
                  norm=Normalize(0,1),interpolation='nearest',aspect='auto',zorder=1)
        artist._target_composition=True
        # Join touching, collinear cell edges; an intact 100x100 grid needs 202 lines.
        segments=grid_segments(np.isfinite(image),x0,z0,gx,dx,dz,factor)
        ax.add_collection(CellEdges(segments,dx/factor,dz/factor,colors='#31475a',linewidths=.65,zorder=1.1),autolim=False)
        bounds=bounds[~regular];values=values[~regular]
    if len(bounds):
        vertices=bounds[:,[0,2,1,2,1,3,0,3]].reshape(-1,4,2)/factor
        blocks=PolyCollection(vertices,cmap=cmap,norm=Normalize(0,1),edgecolors='#31475a',linewidths=.65,zorder=1.2)
        blocks.set_array(values);ax.add_collection(blocks,autolim=False)
