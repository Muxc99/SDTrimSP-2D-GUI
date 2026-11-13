# Target features

Open **Target features…** beside the substrate controls or from the input toolbar. Bulk and surface layer editors are embedded in the first page without a second dialog. Apply changes to the current draft, then save the case to write files. Geometry-26 protrusion drawing retains its existing selection and substrate priority rules.

## Composition precedence

| Order | Input | Effect |
| --- | --- | --- |
| 1 | Substrate / bulk layers | Initial substrate cells |
| 2 | fig.inp protrusion fractions | New geometry-26 blocks; bulk layers are not reapplied |
| 3 | Surface layers | Override substrate and protrusion cells meeting the depth condition |
| 4 | Local file or built-in clusters | Override the selected material cells |

Bulk layers use absolute z. Surface layers display vertical offsets below the local surface (zero at the surface, negative below). The kernel assigns layers by surface-cell index. **The continuous preview is not an exact reconstruction of cut cells.** Layers thinner than geo_dz produce warnings; inspect kernel initial-cell outputs for steps and partially filled cells.

Disable both layer switches, local composition and clusters for a homogeneous substrate. Files may remain for later reuse.

## Substrate composition brush

Two adjacent brushes appear on the main target toolbar. The original brush retains protrusion drawing (or outline-node insertion for geometry 24/25). The green brush with a substrate line edits only local substrate composition. Its independent fractions appear in the right sidebar; they must sum to one. Drag with the left button to paint grid cells without changing geometry or protrusions.

Right-click to edit mixtures, use substrate fractions, sample composition, or toggle erasing local overrides. Erasing restores underlying composition; it does not remove material. Use the main Undo / Redo buttons or Ctrl+Z / Ctrl+Y. The separate Local composition dialog page has been removed.

Strokes create/update doped_zellen_2D.inp and enable l_clust with l_clust_read. Releasing the mouse applies to the case draft; saving writes files. Existing protrusion entries in imported local files are preserved. Built-in clusters must be disabled before painting because the two modes are mutually exclusive.

ix starts at 1 on the left; iz starts at 1 at the grid bottom and increases upwards. Header dimensions must match the grid. After grid changes, synchronize existing local files instead of reinterpreting indices as new physical positions. Partial cells near profiles remain schematic.

## Clusters and materials

Built-in clusters and local files are mutually exclusive. n_clust accepts 1, 4, 9, 16, 25 or 36; qu_clust holds atomic fractions. The engine uses a dedicated placement algorithm that includes random sampling; the GUI preview does not predict the exact random layout.

Choose one, two or three binary compounds using mutually exclusive model flags. Compound names must exist in the external engine material table and both constituent elements must be listed. rhom is in g/cm³; dns_0 is atomic density per species in atoms/A³. -1 uses table values. Internal compound expansion must fit the local version's eight-component limit. Binding energies and other properties are not inferred from formulas.

geo_imax accepts 1 or 2 and controls geometry passes; 2 includes cell reduction. It is not the CPU count. l_alpha_rough_kor enables local rough-surface incidence correction; beam arrows remain reference directions.

## Profiles, distributions and matrices

For geometry 24/25, paste or import x,z columns or generate flat, sine, triangle and finite-slope step profiles. The editor uses centered x and the current display unit; output uses the appropriate geometry coordinates in Angstrom. Applying explicit profile points clears the analytic ripple amplitude to avoid applying it twice. Different heights at the periodic seam produce a warning.

Energy and angle files contain a description line followed by value/weight pairs, **without a count line**. The local 3.01 limits are 100 energy points and 90 angle points. Energies are positive, polar angles are 0–90 degrees, weights are nonnegative and not all zero, and values increase strictly. The local kernel's mode-4 direction-variable issue still needs numerical verification; format validation does not resolve it.

The binding matrix contains a description, component count, one atomic number per line, another description, then ncp x ncp nonnegative values in eV. The template's 1 eV values are placeholders, not material constants. Enabling files synchronizes the mode parameters; disabling allows files to remain. Required files cannot be removed while active.

## Species dependencies and geometry 28

Adding a species appends zero columns to known composition files. Before removing a species, set its fractions to zero in beam, substrate, protrusions, layers and local overrides. Unknown advanced arrays, indexed assignments, active compounds, and binding matrices requiring reconstruction block unsafe changes. Synchronize them explicitly in text rather than silently reinterpreting columns. Replacement preserves positional fractions and resets density overrides to table values; review material properties afterwards.

Geometry 28 provides a specialized schematic and checks for existing inputs only; generic rectangle/local drawing is disabled. The local 3.01 radius is hardcoded to 2510 A when geo_x < 3000 A, otherwise 25010 A. Arbitrary cylinders are not supported by dragging. This geometry is not offered as a general new-case option and requires a matching kernel case for validation.

Compound expansion occurs before these auxiliary files are read. The current editor therefore blocks combining compound flags with layers, local files, clusters, per-block fractions or custom binding matrices, preventing short rows from being misread by the kernel. Compound settings remain available for homogeneous substrates.

New bulk layers start at the highest substrate surface z, independently of beam starting height. Geometry-26 protrusions are not part of bulk-layer substrate initialization. Explicit boundaries in existing files are retained.
