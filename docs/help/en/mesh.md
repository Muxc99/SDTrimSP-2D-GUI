# Mesh, substrate and units

## Settings order

**Grid width and spacing**: geo_dx and geo_dz. **Substrate settings**: geometry, half-width geo_x, bottom geo_z and roughness. **Beam settings**: species, energy, angle, center/width and starting height.

## Dimension example

| Parameter | Example (Å) | Interpretation |
| --- | --- | --- |
| geo_x | 200 | Full width 400 Å=40 nm; x from −200 to +200 Å |
| geo_z | −200 | Flat reference top at 0; bottom at −200 Å |
| geo_dx / geo_dz | 25 / 25 | 16 lateral and 8 reference-depth cells |

In general 2D modes geo_x is an integer multiple of geo_dx. In 1D, geo_dx=2×geo_x gives one lateral cell. Width stays centered about x=0 and the bottom stays level.

## Units

| Quantity | Input unit | Conversion |
| --- | --- | --- |
| Length | Å | 10 Å=1 nm; 10000 Å=1 μm |
| Energy | eV | eV in GUI and input |
| Angle | Degrees | 0° along the reference surface normal |
| Fluence | ions/Å² | 1 ion/Å²=10¹⁶ ions/cm² |
| Atomic density | atoms/Å³ | 1 atom/Å³=10²⁴ atoms/cm³ |

The top unit selector changes display only. Saved lengths remain Å. Equal physical display lengths do not require a square canvas.

