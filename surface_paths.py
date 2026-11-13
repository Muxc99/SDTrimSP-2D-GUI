"""Render rectangular-cell surface traversals without inventing seam edges."""
import numpy as np

def surface_path(frame):
    """Return plot coordinates and an audit frame; original points stay untouched.

    SDTrimSP rectangular boundary edges are axis aligned. A simultaneous x/z
    jump cannot be a cell edge. Opposite-domain endpoint jumps between distinct
    cells are periodic traversal seams, not full-width material boundaries.
    Keep vertical edges, backwards traversal and repeated vertices in order.
    """
    points=frame[['x_A','z_A']].to_numpy(dtype=float)
    n=len(points);reasons=np.full(n,'',dtype=object)
    if n>1:
        span=np.ptp(points[:,0]);scale=max(1.,float(np.max(np.abs(points))))
        tol=max(1e-8,scale*2e-9)
        delta=np.abs(np.diff(points,axis=0))
        diagonal=(delta[:,0]>tol)&(delta[:,1]>tol)
        reasons[1:][diagonal]='non_axis_aligned_jump'
        if span>tol:
            ids=frame['cell_id'].to_numpy()
            wrap=(np.abs(delta[:,0]-span)<=tol)&(ids[1:]!=ids[:-1])
            reasons[1:][wrap]='opposite_boundary_jump'
    breaks=np.flatnonzero(reasons!='')
    plotted=[]
    split=set(breaks)
    for i,point in enumerate(points):
        if i in split:plotted.append([np.nan,np.nan])
        plotted.append(point)
    path=np.asarray(plotted,dtype=float).reshape((-1,2))
    audit=frame.copy()
    audit['connect_from_previous']=(reasons=='')
    if n:audit.loc[audit.index[0],'connect_from_previous']=False
    audit['break_reason']=reasons
    return path,audit
