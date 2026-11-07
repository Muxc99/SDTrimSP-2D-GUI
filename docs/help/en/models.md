# Collision potentials and binding models

## Different roles

| Selector | Controls | Not |
| --- | --- | --- |
| ipot | Interatomic interaction during binary collisions | Beam energy |
| isbv | Binding-energy rule for surface escape | A directly entered eV value |

Menus show numbers and names; hover for 0.5 seconds for details. Native numeric values are saved.

## Collision potentials

| Mode | Name | Meaning |
| --- | --- | --- |
| 1 | Kr-C potential | Kr-C screened interatomic collision potential. Saved as ipot; this is not beam energy. |
| 2 | Molière potential | Molière screened interatomic collision potential; ipot=2. |
| 3 | ZBL potential | Ziegler–Biersack–Littmark universal screened collision potential; ipot=3. |
| 4 | Nakagawa–Yamamura | Local Nakagawa–Yamamura potential branch. Requires compatible integration settings; iintegral=0 is unsupported. |
| 5 | Si potential | Local Si potential branch. Check material applicability and integration settings; iintegral=0 is unsupported. Not a general default. |

## Surface binding models

| Mode | Name | Meaning |
| --- | --- | --- |
| 1 | Fixed per element | Selects the surface escape binding-energy rule, not an energy value in eV. Model 1 uses each species own e_surfb, from material tables or input overrides. |
| 2 | Surface composition mix | Mixes binding energies using surface composition. Pair matrix entries use the surface partner e_surfb; an entry is zero if either binding energy is near zero. |
| 3 | Pair average | Pair binding energies use the arithmetic mean of the two e_surfb values, followed by surface-composition weighting. A pair is zero if either value is near zero. |
| 4 | Compound model | Compound branch: surface terms retain element self values, while compound formation enthalpy modifies bulk binding in the material-table logic. Requires suitable compound data. |
| 6 | Custom binding matrix | Reads the surface-binding matrix from mat_surfb.inp. Supply a file matching the species count and order. Energies are in eV. |
| 7 | Diagonal matrix (advanced) | Advanced local branch: the initial binding matrix has e_surfb only on its diagonal and zero off-diagonal entries. Check applicability to the intended model. |
| 8 | table1a compound model | Special local table1a branch resets surface binding and cutoff energies and includes compound handling. Check the material table and parameters before use. |



Choosing a model does not configure every related advanced parameter or create missing files. isbv=6 needs mat_surfb.inp; compound models require suitable material data.

