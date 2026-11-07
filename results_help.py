"""User-facing result plotting guide, shared with the Help page."""
RESULTS_HELP_ZH='''七、0.7 结果绘图工作台
21 种图像按文件自动启用；使用“图像分类”缩小列表。缺失输出的图像呈灰色。
左侧为绘图设置/数据文件，右侧为固定坐标框绘图区；分隔条可拖动。切换图种时坐标框、色标栏和底部播放条的位置保持不变。二维空间图默认横纵单位长度显示比例为1:1，正方形保持正方形；通过调整显示范围保持坐标框固定，默认将z=0置于中央。
空间单位 Å/nm/μm、注量单位 ions/Å² 或 ions/cm² 可独立切换；形貌统计范围同步换算。

1. 二维分布：元素原子分数、元素数密度、总数密度。
2. 表面与形貌：表面轮廓对比、最高/最低/平均高度、参考高度以上总投影宽度与二维截面积演化。
3. 收支与演化：局部反射与溅射贡献、全靶反射系数与溅射产额、二维单元积分库存量、局部再沉积、动态/静态粒子收支、全局粒子与能量统计。
4. 粒子与轨迹：粒子能谱、出射极角、停止位移/路径、终点位置、独立粒子轨迹。按实际文件与组分筛选。
5. 能量与诊断：带符号能量收支、活跃单元组分收支、入射击中位置、阶段耗时。

绘图区直接左键拖动平移，滚轮围绕鼠标缩放；双击显示全部。上方为紧凑图标工具，0.5秒悬停显示说明，包含平移、框选放大、数据查看、居中和坐标设置。居中菜单可选择z=0或靶表面。坐标设置中可自定义横纵单位显示比例（1为等长，2为横向单位显示长度加倍），也可关闭锁定后分别设置范围，并调整标题、网格和刻度。数据查看只显示实际记录的单元值或最近曲线点；空白处标注为光标坐标。

有多个历史步的空间分布可播放、拖动滑块。固定色标便于比较历史步。
“数据表”在独立浮窗中显示当前图的完整只读数据，不压缩绘图区。拖选、Shift 扩选或 Ctrl 多选；Ctrl+C 复制选区，Ctrl+A 全选，也可右键或点“复制（含列名）”。复制的数据按行列分隔，可直接粘贴到 Excel 等软件，保留数值精度。CSV 导出完整当前图数据。轨迹CSV遵循显示条数上限；直方图CSV为分箱及计数。
PNG 保存当前图。

注意：
反射系数（R）表示入射粒子中被反射出来的比例；例如 R=0.3 表示每入射 100 个粒子约有 30 个被反射。溅射产额（Y）表示每个入射粒子平均打出的靶原子数；例如 Y=0.02 表示每入射 100 个粒子平均打出约 2 个靶原子。两者分别绘制，不表示相除。随注量图显示它们随累计入射注量的变化。“总计”表示各组分之和，反射和溅射仍分别统计。CSV 保留 R_、Y_ 原始列名。
• 局部反射与溅射贡献的分母是全局入射数；局部输运/再沉积文件为原始统计，不能当局部概率。
• 单元积分库存量包含初始基底，除以完整靶投影宽度。E0中的stopped_inventory使用程序自己的归一化。
• E0中cel_qu(maxdep)表示最高点选定单元的成分，不是平均表面成分。
• 宽度表示参考高度以上各段宽度之和；不能直接当单个凸起直径。参考高度附近的微小形变会改变统计。
• 能量保留正负号；粒子/反冲分开，避免把分项与总量重复相加。
• 粒子直方图统计实际记录的抽样粒子，不是产额。出射极角相对程序全局参考，不是局部表面法线。
• 停止位移为z_end-z_start，保留符号，可能包含初始真空飞行段；路径长度是另一物理量。2D不使用x_max/z_max作为最大穿透深度。
• 粒子输出需lparticle_p/lparticle_r与ioutput_part；轨迹需ltraj_p/ltraj_r与numb_hist或ioutput_hist。可在高级参数或输入文件中设置。
• 同次加载须来自同一案例目录。可选输出解析失败会单独提示；不完整核心几何会拒绝载入，保留旧图。
• 单个输出超过64 MiB时不自动读取，并在“数据文件”页说明；不会偷偷截断数据。
'''
RESULTS_HELP_EN='''7. Result workbench 0.7
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
Reflection coefficient (R) is the fraction of incident particles reflected from the target: R=0.3 means about 30 reflected particles per 100 incident particles. Sputtering yield (Y) is the mean number of target atoms ejected per incident particle: Y=0.02 means about 2 ejected atoms per 100 incident particles. These are separate quantities, not a division. The fluence plot shows their evolution with cumulative incident fluence. Total means the sum across species, with reflection and sputtering kept separate. CSV retains the original R_ and Y_ column names.
Local reflection and sputtering contributions use the GLOBAL incident denominator. Transport/redeposition are raw statistics, not local probabilities.
Cell-integrated inventory includes initial substrate and uses full projected width. E0 stopped_inventory uses program normalization.
cel_qu(maxdep) is composition of the selected top cell, not mean surface composition.
Projected width sums intervals above the chosen reference, not an individual pillar diameter. Small shifts near the reference affect this measure.
Preserve signed energy terms and distinguish totals/components and projectile/recoil groups.
Particle histograms use recorded samples, not yields. Exit angles use the program global reference, not local surface normals.
Stopping displacement is signed z_end-z_start and may include initial vacuum flight. Path length is separate. 2D maximum-coordinate placeholders are not used as penetration depths.
Particle outputs require lparticle_p/lparticle_r and ioutput_part; trajectories require ltraj_p/ltraj_r and numb_hist or ioutput_hist.
Load one case directory at a time. Invalid optional files are reported separately; invalid core geometry retains the previous results.
Files above64 MiB are explicitly skipped in the file inventory; they are never silently truncated.
'''
