"""界面文字切换；不翻译输入值、原始文件、组分名称或日志。"""
from PySide6.QtCore import QObject,QEvent
from PySide6.QtWidgets import (QWidget,QLabel,QAbstractButton,QGroupBox,QComboBox,
                              QTabWidget,QTableWidget,QLineEdit,QMessageBox)

PAIRS = [
('点击元素名或“…”选择元素；点击 × 删除，点击 ＋ 新增空白元素。材料属性可直接编辑，仅用于当前运行，不修改原始材料表或案例输入。','Click an element or ... to select a species; × removes it and + adds a blank entry. Edit material properties directly; they apply only to this run and do not change the source table or case input.'),
('点击选择元素 / 同位素 / 材料条目','Click to select element / isotope / material'),
('添加空白元素','Add blank species'),('删除此元素','Remove this species'),
('请点击空白元素行的“…”选择元素。','Click ... in each blank species row to select an element.'),
('保存（Ctrl+S）','Save (Ctrl+S)'),('另存为…（Ctrl+Shift+S）','Save as… (Ctrl+Shift+S)'),
('新建案例…（Ctrl+N）','New case… (Ctrl+N)'),('长度','Length'),('语言 / Language','语言 / Language'),
('SDTrimSP-2D  /  中文输入工作台','SDTrimSP-2D  /  Input Workbench'),
('3.01 内核 · 一维 / 平面 / 轮廓 / 矩形 / 余弦表面 · 扩展参数与附件保留 · 中文输入工作台 0.3',
 '3.01 engine · 1D / flat / profile / rectangles / cosine surface · Extended inputs preserved · Workbench 0.3'),
('v1.0.0 · 保存更新当前案例；另存与运行使用新目录 · 预览为初始轮廓/分层示意，非内核运算结果',
 'v1.0.0 · Save updates current case; Save as and run use new directories · Preview shows initial geometry, not simulation results'),
('打开案例…','Open case…'),('另存为新案例…','Save as new case…'),('检查输入','Check input'),
('运行当前输入','Run input'),('请求停止','Request stop'),('打开结果目录','Open run folder'),
('显示长度单位','Length unit'),('本地示例','Local examples'),
('载入所选案例','Load selected case'),('案例与元素 / 束流','Case, species and beam'),
('案例标题','Case title'),('分数均为原子分数（0～1）；束流和基底各自合计为1。','Atomic fractions (0–1); beam and substrate must each sum to 1.'),
('元素','Species'),('束流分数','Beam fraction'),('能量 / eV','Energy / eV'),('入射角 / °','Angle / °'),
('基底分数','Substrate fraction'),('浓度上限','Concentration limit (engine)'),('选择元素 / 同位素…','Select element / isotope…'),
('原子质量 u','Atomic mass u'),('质量密度 g/cm³','Mass density g/cm³'),('原子数密度 atoms/Å³','Atomic number density atoms/Å³'),
('浓度上限（内核）','Concentration limit (engine)'),
('qu_max：动态靶中该组分允许达到的最高原子分数，范围 0～1。1 表示不设有限上限；当前内核最多支持两个 0<qu_max<1 的组分。','qu_max: maximum allowed target atomic fraction for this species in a dynamic target (0–1). 1 means no finite limit; this engine supports at most two species with 0<qu_max<1.'),
('材料参数不完整','Incomplete material properties'),
('请为以下组分填写大于0的原子质量、质量密度和原子数密度：','Enter positive atomic mass, mass density, and atomic number density for: '),
('添加元素','Add species'),('删除选中元素','Remove species'),('靶区 / 网格 / 入射位置','Target, mesh and incidence'),
('几何类型','Geometry'),('横向半宽','Lateral half-width'),('基底底部（负值）','Bottom z (negative)'),
('横向网格间距','Mesh spacing x'),('竖向网格间距','Mesh spacing z'),('束斑中心','Beam center x'),
('束斑宽度','Beam width'),('入射起始高度','Starting height'),('粗糙振幅 pr_amp','Roughness pr_amp'),
('粗糙周期 pr_wl','Roughness pr_wl'),('总宽 = 2 × geo_x；geo_z 为负值。\n保存时长度统一转换为 Å。',
 'Total width = 2 × geo_x; geo_z is negative.\nSaved lengths use Å.'),
('计算设置','Calculation'),('动态更新靶材','Dynamic target'),('起点模式','Starting position mode'),
('能量模式','Energy mode'),('角度模式','Angle mode'),('局部表面起射','Local surface'),('固定坐标','Fixed coordinate'),
('均匀随机束斑','Uniform random beam'),('相对表面（高级）','Relative to surface (advanced)'),
('特殊分布（高级）','Special distribution (advanced)'),('规则采样（高级）','Regular sampling (advanced)'),
('固定能量','Fixed energy'),('固定角度','Fixed angle'),('分布模式（高级）','Distribution (advanced)'),
('保留输入','Preserved input'),('参数保留模式','Preserved parameters'),
('注量（ions/Å²）','Fluence (ions/Å²)'),('注量步数','Fluence steps'),('输出间隔（步）','Output interval (steps)'),
('每步入射抽样数','Projectiles per step'),('碰撞势编号','Potential model ID'),('表面结合能模型编号','Surface binding model ID'),
('入射角相对参考表面法线，0°为垂直。\n势编号：1 Kr-C / 2 Molière / 3 ZBL。\nisbv 是模型编号，不是结合能数值。',
 'Angle from reference surface normal; 0° is normal.\nPotential: 1 Kr-C / 2 Molière / 3 ZBL.\nisbv is a model ID, not a binding energy.'),
('着色元素','Color by species'),('显示入射起始面','Show starting plane'),
('参数设置与预览','Input and preview'),('二维结构块','2D structure blocks'),('高级参数','Advanced parameters'),
('轮廓与辅助文件','Profiles and auxiliary files'),('输入文件预览','Input file preview'),('运行日志','Run log'),
('导入诊断','Import diagnostics'),('结果绘图','Result plots'),('使用说明','Help'),
('fig.inp：每行一个矩形块；镜像时只填写 x≥0 一侧。大结构需按基础网格拆分。',
 'fig.inp: one rectangle per row; use x≥0 for mirrored structures. Split large structures into base mesh cells.'),
('关于 x=0 左右镜像','Mirror about x=0'),('每个块单独指定成分','Specify composition per block'),
('添加块','Add block'),('复制选中块','Duplicate blocks'),('删除选中块','Remove blocks'),
('关闭逐块成分时，程序使用基底成分；隐藏的成分列不用于 fig.inp 输出。',
 'Without per-block composition, the engine uses substrate fractions; hidden fractions are omitted from fig.inp.'),
('高级参数保留原 Fortran 写法（长度仍为 Å）。未编辑的项目逐字保留；更改后请核对内核手册。',
 'Advanced values use Fortran syntax (lengths in Å). Unedited fields are preserved; check the engine manual before editing.'),
('参数名（只读）','Parameter (read-only)'),('值 / Fortran 表达式','Value / Fortran expression'),
('轮廓与分层文件可直接编辑；本页坐标始终为 Å，不随右上角单位切换。修改实时检查，保存/运行使用当前内容。',
 'Edit profile/layer files directly. Coordinates here always use Å. Current contents are checked and used for save/run.'),
('当前表单生成的文件预览。未编辑的扩展参数保留；本页只读。',
 'Read-only preview of generated inputs. Unedited extended parameters are preserved.'),
('选择元素 / 同位素 / 材料条目','Select element / isotope / material'),
('搜索材料名、元素符号或原子序数，如 D、He3、C_g、W、74','Search material, element or atomic number: D, He3, C_g, W, 74'),
('表内名称','Table symbol'),('质量 / u','Mass / u'),('类型','Type'),('镧系','Lanth.'),('锕系','Actin.'),
('使用所选条目','Use selection'),('取消','Cancel'),('全部可用条目','All available entries'),
('氢 / 表内质量','Hydrogen / table mass'),('质量与 D 相同的表内别名','Table alias with the same mass as D'),
('氘 / 氢-2','Deuterium / H-2'),('氚 / 氢-3','Tritium / H-3'),('氦-3','Helium-3'),
('氦 / 表内质量','Helium / table mass'),('硼-10','Boron-10'),('硼-11','Boron-11'),
('材料 / 表内变体','Material variant'),('元素 / 表内质量','Element / table mass'),
('列表只提供本机 table1 的有效名称；材料变体不是同位素。\nH2 在此表中的质量与 D 相同（2.014083 u）。\n这里只选择单个表内条目，不自动展开天然同位素混合物。',
 'Only names available in local table1 are offered; material variants are not isotopes.\nH2 has the same table mass as D (2.014083 u).\nSelection does not expand natural isotope mixtures.'),
('没有匹配的条目。','No matching entries.'),('材料表读取失败','Cannot read material table'),
('双击第一列，打开元素 / 同位素选择器；其余数值直接编辑。','Double-click the first column to select species; edit other values directly.'),
('双击选择元素 / 同位素 / 材料条目','Double-click to select element / isotope / material'),
('打开结果目录…','Open results folder…'),('选择输出文件…','Select output files…'),('载入本次运行结果','Load current run results'),
('导出当前数据 CSV…','Export current data CSV…'),('保存图片 PNG…','Save plot PNG…'),
('尚未载入结果。请选择同一算例的输出目录或文件。','No results loaded. Select output files or a folder from one case.'),
('显示物理量','Quantity'),('空间单位','Space unit'),('注量单位','Fluence unit'),('组分','Component'),
('注量 / 历史步','Fluence / history'),('叠加同一步表面轮廓','Overlay matching surface'),
('轮廓对比：选择多个历史步','Surface comparison: select snapshots'),('反射系数与溅射产额：选择曲线','Reflection coefficient and sputtering yield: select curves'),
('元素原子分数','Atomic fraction'),('元素数密度','Element number density'),('总原子数密度','Total number density'),
('表面轮廓对比','Surface comparison'),('局部反射与溅射贡献','Local reflection and sputtering contributions'),('反射系数与溅射产额随注量','Reflection coefficient and sputtering yield vs fluence'),
('选择结果目录','Select results folder'),('选择同一算例的二维输出文件','Select 2D outputs from one case'),
('结果读取失败','Cannot load results'),('导出失败','Export failed'),('导出当前数据 CSV','Export current data CSV'),
('保存图片 PNG','Save plot PNG'),('尚无本次运行','No current run'),('计算仍在运行','Calculation running'),
('请等待计算结束后载入完整输出。','Wait for the calculation to finish before loading complete outputs.'),
('请先运行案例，或使用“打开结果目录”。','Run a case first, or open an existing results folder.'),
('保存成功','Saved'),('保存失败','Save failed'),('无法运行','Cannot start run'),('元素数量','Species count'),
('试用版最多支持8种元素。','This build supports at most 8 species.'),('尚未另存','Unsaved changes'),
('当前有未另存的编辑。是否放弃并关闭？','Discard unsaved changes and close?'),
('请先请求停止并等待计算结束，再关闭窗口。','Request stop and wait for the calculation to finish before closing.'),
('工作台已打开','Workbench already open'),('输入参数：','Input parameter: '),
('输入检查通过；计算结果仍需验证收敛与物理适用性。','Input checks passed; convergence and physical applicability still require validation.'),
('确定','OK'),('是(&Y)','&Yes'),('否(&N)','&No'),
('一维平面','1D flat'),('二维平面','2D flat'),('轮廓（0～总宽）','Profile (0 to full width)'),
('轮廓（中心坐标）','Profile (centered)'),('矩形块','Rectangular blocks'),('余弦表面','Cosine surface'),
('矩形结构 fig.inp','Rectangles fig.inp'),
('案例信息','Case information'),
('本地示例\n选择案例后，点击右侧箭头载入。','Local examples\nChoose a case, then click the arrow to load it.'),
('请求停止\n内核每10个注量步检查一次，请等待安全结束。','Request stop\nThe engine checks every 10 fluence steps; wait for a safe stop.'),
('靶绘制','Target drawing'),('靶区 / 基底 / 网格','Target / substrate / mesh'),
('显示网格','Show grid'),('覆盖已占用网格','Replace occupied cells'),
('关闭时跳过已有材料格；开启时以本次绘制替换整个材料格。','Off: skip occupied cells. On: replace the whole occupied material cell.'),
('基底成分（原子分数）','Substrate composition (atomic fraction)'),('凸起设置','Protrusion settings'),
('新绘制块成分（原子分数）','New block composition (atomic fraction)'),
('采用基底成分','Use substrate'),('采用选中块成分','Use selected'),
('选择 / 框选（右键编辑，Alt+拖动移动）','Select / marquee (right-click edits; Alt+drag moves)'),
('画笔：按网格涂绘','Brush: paint grid cells'),('橡皮擦：删除整个凸起块，不擦除基底','Eraser: remove whole protrusion blocks; preserve substrate'),
('矩形：自动按网格切分','Rectangle: split along grid boundaries'),('椭圆：矩形网格近似','Ellipse: rectangular grid approximation'),
('平移画面','Pan view'),('放大','Zoom in'),('缩小','Zoom out'),('适应全部靶区','Fit entire target'),
('撤销绘图操作（Ctrl+Z）','Undo drawing (Ctrl+Z)'),('重做绘图操作（Ctrl+Y）','Redo drawing (Ctrl+Y)'),
('删除选中的凸起块','Delete selected protrusion blocks'),
('选择：单击选块、拖框多选；右键编辑，Ctrl+C/X/V 复制剪切粘贴；方向键换选，Alt+拖动移动。','Select: click a block or drag a selection. Right-click edits; Ctrl+C/X/V copy/cut/paste, arrows navigate, Alt+drag moves.'),
('fig.inp · 矩形块坐标 / 成分','fig.inp · Rectangle coordinates / fractions'),
('每行一个矩形；成分顺序与元素表一致。','One rectangle per row; component order matches the species table.'),
('输入文件','Input files'),
('tri.inp、fig.inp 及辅助文件均可编辑。文本修改经检查后同步参数表和绘图，并用于另存与运行；文件内长度始终为 Å。',
 'tri.inp, fig.inp and auxiliary files are editable. Validated text edits update parameters and drawing and are used for save/run. File lengths always use Å.'),
('应用文本修改','Apply text edits'),('撤销未应用文本','Discard unapplied text'),
]
PAIRS+=[('导出动画 GIF…', 'Export animation GIF…'), ('绘图设置', 'Plot settings'), ('数据文件', 'Data files'), ('图像与单位', 'Plot and units'), ('图像类型', 'Plot type'), ('各历史步使用固定色标', 'Use fixed color scale across snapshots'), ('形貌统计范围', 'Morphology range'), ('取样 x', 'Sample x'), ('取样 z', 'Sample z'), ('形貌 x 最小值', 'Morphology x minimum'), ('形貌 x 最大值', 'Morphology x maximum'), ('参考高度 z', 'Reference height z'), ('剖面物理量', 'Profile quantity'), ('原子分数', 'Atomic fraction'), ('原子数密度', 'Atomic number density'), ('数据来源与统计', 'Data source and statistics'), ('文件 / 分组', 'File / group'), ('粒子组分', 'Particle species'), ('直方图分箱', 'Histogram bins'), ('显示轨迹上限', 'Trajectory display limit'), ('轮廓对比：选择历史步', 'Surface comparison: snapshots'), ('选择曲线 / 统计项', 'Curves / quantities'), ('全选', 'Select all'), ('清空选择', 'Clear selection'), ('查看文件与输出选项说明', 'File and output options help'), ('数据表', 'Data table'), ('播放', 'Play'), ('暂停', 'Pause'), ('截面积', 'Cross-sectional area'), ('保留面密度', 'Retained areal density'), ('粒子计数', 'Particle counts'), ('能量', 'Energy'), ('最高点成分', 'Top-cell composition'), ('表面高度', 'Surface height'), ('组分收支', 'Component balance'), ('体积诊断量', 'Volume diagnostic')]
PAIRS+=[('图像分类', 'Plot category'), ('全部图像', 'All plots'), ('二维分布', '2D distributions'), ('表面与形貌', 'Surface and morphology'), ('收支与演化', 'Balances and evolution'), ('粒子与轨迹', 'Particles and trajectories'), ('能量与诊断', 'Energy and diagnostics')]
PAIRS += [('碰撞势','Collision potential'),('表面结合能模型','Surface binding model'),('当前几何类型','Current geometry'),('入射组分','Incident species'),('入射角 / °','Incidence angle / °'),('入射角上限 / °','Angle upper limit / °'),('入射角中心 / °','Angle center / °')]
PAIRS += [('元素','Elements'),('网格/基底/束流','Mesh / substrate / beam'),('凸起成分（原子分数）','Protrusion composition (atomic fractions)'),('网格宽度与间距','Grid width and spacing'),('基底设置','Substrate settings'),('束流设置','Beam settings'),('束流能量 / eV','Beam energy / eV'),('能量中心 / eV','Energy center / eV'),('温度能量 kT / eV','Thermal energy kT / eV')]
PAIRS += [('内核设置','Engine settings')]
PAIRS += [('关于与诊断','About and diagnostics'),
 ('标准元素符号（未配置材料表）','Standard element symbol (no material table)'),
 ('未配置材料表：可选择标准元素符号进行编辑；运行前需用外部 table1 核验。','No material table: standard symbols are available for editing; verify against external table1 before running.'),
 ('未配置材料表；此处不提供质量或密度数据。','No material table configured; mass and density data are unavailable.'),
 ('数据来源：已配置的外部计算内核材料表','Source: configured external engine material table')]
PAIRS += [('基底画笔成分（原子分数）','Substrate brush composition (atomic fractions)'),('靶材功能…','Target features…'),('分层成分编辑…','Layer composition editor…'),('保存','Save'),('撤销','Undo'),('重做','Redo'),('添加文件…','Add file…'),('导入文件…','Import file…'),('移除文件','Remove file'),('上一处','Previous'),('下一处','Next')]
ZH_TO_EN=dict(PAIRS)
EN_TO_ZH={en:zh for zh,en in PAIRS}
FRAGMENTS=[('同位素 / 材料条目','Isotope / material entries'),('搜索结果','Search results'),
           ('几何 ','Geometry '),(' 周期错误：总宽 ',' periodicity error: width '),
           (' Å 与 pr_wl ',' A and pr_wl '),(' Å 不匹配（总宽/pr_wl=',' A are incompatible (width/pr_wl='),
           ('，需为整数）。',', which must be an integer).'),
           ('周期错误：内核要求 int(pr_wl)>0；当前 pr_wl 小于 1 Å。','Period error: the engine requires int(pr_wl)>0; current pr_wl is below 1 A.'),
           (' 个条目',' entries'),('质量：','Mass: '),('质量密度：','Mass density: '),
           ('原子数密度：','Atomic number density: '),('数据来源：本机','Source: local'),
           ('源案例：','Source case: '),('矩形结构 fig.inp','Rectangles fig.inp'),
           ('一维平面','1D flat'),('二维平面','2D flat'),('轮廓（0～总宽）','Profile (0 to full width)'),
           ('轮廓（中心坐标）','Profile (centered)'),('余弦表面','Cosine surface'),
           ('动态','Dynamic'),('静态','Static'),('总宽 ','Total width '),('基底厚 ','Substrate thickness '),
           ('基础网格 ','Base mesh '),('入射抽样 ','Sampled projectiles '),('总注量 ','Total fluence '),
           ('案例已导入；原输入文件未修改。','Case loaded; original inputs preserved.')]

def translated(text,language):
    pairs=ZH_TO_EN if language=='en' else EN_TO_ZH
    if text in pairs:return pairs[text]
    # 数字前缀的模式项保留原始内核编号。
    if ' · ' in text:
        prefix,suffix=text.split(' · ',1)
        if prefix.isdigit() and suffix in pairs:return prefix+' · '+pairs[suffix]
    for zh,en in sorted(FRAGMENTS,key=lambda item:len(item[0]),reverse=True):
        text=text.replace(zh,en) if language=='en' else text.replace(en,zh)
    return text

class InterfaceLanguage(QObject):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.busy=False

    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.Show and isinstance(obj,QWidget) and obj.isWindow():
            # 应用内弹窗在显示前沿用当前语言。
            if obj is self.owner or self.owner.isAncestorOf(obj):self.apply(obj)
        return False

    def apply(self,root):
        if self.busy:return
        self.busy=True
        try:
            language=self.owner.ui_language
            for widget in [root]+root.findChildren(QWidget):
                was=widget.blockSignals(True)
                try:
                    widget.setWindowTitle(translated(widget.windowTitle(),language))
                    widget.setToolTip(translated(widget.toolTip(),language))
                    widget.setAccessibleName(translated(widget.accessibleName(),language))
                    widget.setStatusTip(translated(widget.statusTip(),language))
                    if isinstance(widget,(QLabel,QAbstractButton)):
                        widget.setText(translated(widget.text(),language))
                    if isinstance(widget,QMessageBox):
                        widget.setText(translated(widget.text(),language))
                        widget.setInformativeText(translated(widget.informativeText(),language))
                    if isinstance(widget,QGroupBox):widget.setTitle(translated(widget.title(),language))
                    if isinstance(widget,QLineEdit):widget.setPlaceholderText(translated(widget.placeholderText(),language))
                    if isinstance(widget,QComboBox):
                        for i in range(widget.count()):widget.setItemText(i,translated(widget.itemText(i),language))
                    if isinstance(widget,QTabWidget):
                        for i in range(widget.count()):widget.setTabText(i,translated(widget.tabText(i),language))
                    if isinstance(widget,QTableWidget):
                        for i in range(widget.columnCount()):
                            item=widget.horizontalHeaderItem(i)
                            if item:item.setText(translated(item.text(),language))
                        if widget.objectName()=='material_entries':
                            for i in range(widget.rowCount()):
                                item=widget.item(i,2)
                                if item:item.setText(translated(item.text(),language))
                finally:widget.blockSignals(was)
        finally:self.busy=False
