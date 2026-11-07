# 26: protrusion editing

## Protrusions have priority

Material/empty cell selection, brush, eraser, rectangle, context menus and clipboard take priority. Substrate handling has the lowest priority. Select inside the substrate at z<0 before its handles appear. Returning to the protrusion region or changing drawing tools deselects it; blank z≥0 cells remain editable.

## Tools and fractions

| Tool | Action |
| --- | --- |
| Select | Click cells or drag a selection; Ctrl adds; arrows navigate |
| Brush | Paint whole cells using Protrusion composition |
| Rectangle | Split the dragged area at mesh boundaries, retaining partial edges |
| Eraser | Remove whole blocks, preserving substrate |
| Pan | Drag view; middle button also pans; wheel zooms |

Use substrate or selected-block composition as a preset. Per-block composition writes fractions to fig.inp; disabling it uses substrate fractions. Brush and rectangle drawing replace material in occupied cells by default.

## Editing and clipboard

Right-click to resize, change fractions, bulk fill/change material or move. Alt+drag snaps movement to the mesh. Ctrl+C/X/V copies/prepares a cut/pastes. Source removal occurs only after successful paste. Empty cells retain layout offsets without generating fake material. Mirroring links both sides; draw on the right. Collision or bounds violations reject the complete edit.

## Substrate and undo

Select the substrate to resize sides/bottom corners. Existing blocks retain their sizes; shrinking beyond a block is rejected. Ctrl+Z/Y undo/redo. Manual table or mesh edits can reset drawing history.


## Displaying many blocks

Large sets of full mesh cells use a batched raster display; partial cells retain exact rectangular edges. This only changes rendering: material blocks in fig.inp are neither merged nor removed. Material-cell edges hide below 3 pixels per cell and return on zoom-in; Show grid still controls the background mesh. Selection and brush previews refresh independently, and color gradients remain editable live.
