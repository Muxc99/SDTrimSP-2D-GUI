# Geometry and profile files

## Mode reference

| case_geo | Structure | Main inputs |
| --- | --- | --- |
| 10 | 1D flat | geo_x, geo_z; one lateral cell |
| 20 | 2D flat | Mesh and substrate dimensions |
| 24 | Upper polyline, file origin at left edge | rauh.inp: usually x=0 to full width |
| 25 | Upper polyline, centered file x | rauh.inp: usually −geo_x to +geo_x |
| 26 | Flat substrate plus rectangle blocks | fig.inp |
| 27 | Cosine surface | pr_amp, pr_wl |

Choose geometry when creating a case. Target drawing displays its number/name. Both profile modes use centered canvas coordinates; saving converts to their file conventions.

## Minimal rauh.inp

Mode 24, full width 400 Å:

~~~text
surface profile
3
0    0
200  50
400  0
~~~

Mode 25 uses x=−200,0,200 instead. Points must increase strictly in x and cover the full width. Adjacent points interpolate linearly. Only the top is defined; geo_z remains the bottom. Single-valued z(x) cannot represent caves or overhangs.

## Cosine surface

z(x)=pr_amp×[1−cos(2πx/pr_wl)]; peak-to-valley height is 2×pr_amp. Modes 24/25 can also include cosine modulation. Distinguish the orange base profile from the modulated surface.

