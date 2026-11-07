# 24/25: outline editing

## Select, then drag

Handles are hidden until selected. Click the substrate with Select to show upper nodes, side/bottom handles and both bottom corners. Hover changes the cursor. Click outside or press Escape to deselect. Substrate editing takes priority in these modes.

## Add a fifth node

1. Two upper endpoints and two bottom corners initially form a closed rectangle.
2. Activate Add node on edge and click an upper segment.
3. Switch to Select and drag the new node to a mesh intersection.
4. Add more nodes or delete a selected interior node. Endpoints cannot be deleted.

## Sides, bottom and corners

Sides change centered width and scale profile x positions. The bottom changes geo_z; bottom corners change width and depth together. The bottom remains level. Upper points cannot cross or reach below the bottom. Endpoint corners can change endpoint height and width. Size/file changes are atomic and support mixed undo with node edits.

## Files and preview

Mode 24 saves left-edge x; 25 saves centered x. All lengths are Å. Parameters, rauh.inp and previews synchronize; trailing source content is retained. Reset rectangle restores two base endpoints at z=0 while retaining additional cosine settings.

