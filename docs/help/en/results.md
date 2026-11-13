# Plots and physical quantities

Surface curves retain original traversal order and vertical faces. Opposite-boundary and diagonal non-cell-edge jumps are disconnected. All raw points remain; exported data includes connect_from_previous and break_reason. Invalid cells are reported separately: splitting a curve does not repair engine output.

## Outputs and plots

Load files from one case directory. All 21 plots depend on actual outputs; unavailable plots are disabled, never synthesized.

| Plot | Output |
| --- | --- |
| Atomic fractions | T_10_2D.dat |
| Species number density | T_10_2D.dat |
| Total number density | T_10_2D.dat |
| Surface comparison | surf.dat |
| Local reflection and sputtering contributions | sputter_yield.dat |
| Reflection coefficient and sputtering yield vs fluence | sputter_yield.dat |
| Projected-area inventory vs fluence | T_10_2D.dat |
| Height / width / area evolution | T_10_2D.dat |
| Local redeposition | re_deposit.dat |
| Local particle balance | loss_depos.dat |
| Static local particle balance | loss_depos_2.dat |
| Incident hit distribution | surf_proj.dat |
| Global particle / energy statistics | E0_31_3D.dat |
| Signed energy budget | energy_analyse.dat |
| Particle energy spectrum | partic_*.dat |
| Particle polar-angle distribution | partic_*.dat |
| Stopped displacement / path distribution | partic_*.dat |
| Particle endpoint positions | partic_*.dat |
| Particle trajectories x–z | trajec_*.dat |
| Active-cell component balance | activ_cell.dat |
| Computation time by stage | time00.dat |

## Choose a plot

Use 2D distributions for composition/density, surface/morphology for heights/projected widths/2D areas, balances for reflection/sputtering/inventory/redeposition, and particle plots for recorded samples. Filter with Plot category, then select species, snapshot and units.

## Distinctions

Reflection coefficient (R) is the fraction of incident particles reflected from the target: R=0.3 means about 30 reflected particles per 100 incident particles. Sputtering yield (Y) is the mean number of target atoms ejected per incident particle: Y=0.02 means about 2 ejected atoms per 100 incident particles. These are separate quantities, not a division. The fluence plot shows their evolution with cumulative incident fluence. Total means the sum across species, with reflection and sputtering kept separate. CSV retains the original R_ and Y_ column names.

Local reflection and sputtering contributions use the global incident denominator; whole-target coefficients and yields sum across x. Local contributions are not local probabilities. Inventory includes the initial substrate. Width is the sum of projected intervals above a reference, not a single protrusion diameter. Top-cell composition is not a surface average. Preserve signed energy. Histograms count recorded samples, not yields.

Stopping displacement is z_end−z_start and can include vacuum flight; path length is separate. Exit angles use a global reference, not local normals. Data are not smoothed or automatically renormalized.

## Detailed conventions

7. Result workbench 0.7
21 plot types are enabled according to available outputs. Plot category narrows the list. Missing outputs disable the corresponding plots.
Settings and file inventory occupy the left pane; the main figure uses a fixed axes rectangle on the right. Drag the divider to adjust widths. Plot types share the same axes and reserved colorbar/playback positions. Spatial plots default to equal displayed physical unit lengths: squares remain square. Limits expand inside the fixed axes rectangle, with z=0 centered by default.
Space and fluence units are independent. Physical morphology ranges are preserved on unit changes.

2D distributions: species atomic fractions, species number densities and total number density.
Surface / morphology: surface comparisons, heights, projected width and 2D cross-sectional areas versus fluence.
Balances / evolution: local reflection/sputtering contributions and whole-target reflection coefficients/sputtering yields, integrated inventory, redeposition, dynamic/static transport, global particle/energy statistics.
Particles / trajectories: energy, exit polar angle, stopping displacement/path, endpoints and independent trajectories.
Energy / diagnostics: signed energy budgets, active-cell balance, incident hits and computation timings.

Drag to pan, wheel-zoom at the cursor, and double-click to fit all data. Compact icons show tooltips after0.5 seconds. Tools include pan, box zoom, data tips, centering and axis settings. Center on z=0 or the target surface. In Axes, customize the horizontal/vertical physical unit display ratio (1 means equal lengths; 2 doubles horizontal unit length), or unlock independent ranges. Titles, grid and tick intervals are editable. Data tips use actual cell/curve records; blank areas are explicitly labeled cursor coordinates.

Play or scrub spatial distributions across recorded snapshots. Fixed color scales aid comparison.
Data table opens the complete current plotted dataset in a separate read-only floating window without resizing the plot. Drag, Shift-extend or Ctrl-select cells; Ctrl+C copies the selection and Ctrl+A selects all. Right-click or use Copy with headers to include column names. Clipboard data preserves row/column layout and numeric precision for pasting into spreadsheets. CSV exports the full current plotted dataset. Trajectory limits and histogram bins are reflected in CSV.
PNG saves the current plot.

Conventions:
Local reflection and sputtering contributions use the GLOBAL incident denominator. Transport/redeposition are raw statistics, not local probabilities.
Cell-integrated inventory includes initial substrate and uses full projected width. E0 stopped_inventory uses program normalization.
cel_qu(maxdep) is composition of the selected top cell, not mean surface composition.
Projected width sums intervals above the chosen reference, not an individual pillar diameter. Small shifts near the reference affect this measure.
Preserve signed energy terms and distinguish totals/components and projectile/recoil groups.
Particle histograms use recorded samples, not yields. Exit angles use the program global reference, not local surface normals.
Stopping displacement is signed z_end-z_start and may include initial vacuum flight. Path length is separate. 2D maximum-coordinate placeholders are not used as penetration depths.
Particle outputs require lparticle_p/lparticle_r and ioutput_part; trajectories require ltraj_p/ltraj_r and numb_hist or ioutput_hist.
Files above64 MiB are explicitly skipped in the file inventory; they are never silently truncated.




## Invalid cell boundaries and output precision

Legacy T_10_2D.dat writes coordinates with five significant digits. Thin dynamic cells can appear to have zero width or height. Affected histories are explicitly listed and excluded as entire snapshots; valid histories and independent surface/yield files remain available. No cell widths are invented and no individual cells are removed from retained snapshots. Inventory and morphology use only valid snapshots; lines spanning missing histories do not reconstruct data. Structural, finite-value, density and cell-ID checks remain active.

Future GUI runs use a separate executable with higher coordinate output precision. The original executable is retained. Precision lost in existing files cannot be recovered exactly; rerun the original inputs for complete histories.

## Displaying many result cells

Atomic-fraction, species-density and total-density maps draw original rectangular cells in batches, retaining deformed boundaries and empty regions without interpolation, smoothing or cell merging. History/species changes reuse axes, the colorbar and validated geometry. Fixed color limits still cover all histories. Inventory and morphology calculations are cached and recomputed when their parameters or the dataset change. Display caches do not modify output files or CSV values.
