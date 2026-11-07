# Plot navigation and export

## Mouse and toolbar

| Action | Effect |
| --- | --- |
| Left or middle drag | Pan, unless box/data tool is active |
| Wheel at cursor | Zoom around pointer |
| Box zoom | Drag a rectangle to enlarge |
| Double-click / Fit | Show all data |
| Back / Forward | Restore previous views |
| Data tips | Real cell/curve values; blank areas show cursor coordinates |

Tooltips appear after 0.5 seconds. Initial preview and results share navigation; a preview remains an input sketch.

## Axes and ratio

Physical unit display lengths default to 1:1 with z=0 centered. The canvas need not be square. Center menu also supports the surface. Axes edits ranges, unit ratio, titles, grid and ticks, and can unlock independent ranges. The ratio shortcut was removed; Axes retains the setting.

## Export and snapshots

Data table opens the complete current plotted dataset in a separate read-only floating window without resizing the plot. Drag, Shift-extend or Ctrl-select cells; Ctrl+C copies the selection and Ctrl+A selects all. Right-click or use Copy with headers to include column names. Clipboard data preserves row/column layout and numeric precision for pasting into spreadsheets. CSV exports the full current plotted dataset. Exports respect the selected trajectory limit and histogram bins. _A coordinates and fluence_ions_A2 retain original units. PNG saves the plot. GIF button is removed. Play/scrub multiple snapshots; fixed color scales aid comparisons.


## Custom color gradient

For atomic-fraction, species-density and total-density maps, click the Color gradient toolbar icon (left of Save PNG), or double-click the colorbar. The initial target preview supports both entry points. On the target drawing page, double-click the plot or the atomic-fraction color scale. The initial preview and target drawing share a palette per element; result palettes are independent.

Drag any of four stops to change its position; double-click a stop or click Stop color to select a color. Position can also be entered as a percentage. Preview is live; OK keeps changes and Cancel restores the previous palette. Positions are percentages of the colorbar range; data, color limits and coordinates remain unchanged. Palettes are retained in the current window.

The palette is retained for the same plot type and species when switching histories in the current window. PNG uses the selected palette; CSV values are unchanged. The button is disabled for plots without a colorbar.
