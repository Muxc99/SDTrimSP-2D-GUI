"""模式短名称和双语说明；仅作用于界面，不修改内核或输入值。"""
from html import escape
from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QToolTip
from element_picker import NoWheelComboBox

# 编号与本机 projectile.F90 / 几何输入约定对应。
# 每项为：编号、中文短名、英文短名、中文说明、英文说明。
MODE_OPTIONS = {
    'ipot': (
        (1,'Kr-C 势','Kr-C potential','Kr-C 屏蔽原子间碰撞势。编号写入 ipot；不是束流能量。','Kr-C screened interatomic collision potential. Saved as ipot; this is not beam energy.'),
        (2,'Molière 势','Molière potential','Molière 屏蔽原子间碰撞势；输入文件中 ipot=2。','Molière screened interatomic collision potential; ipot=2.'),
        (3,'ZBL 势','ZBL potential','Ziegler–Biersack–Littmark 通用屏蔽碰撞势；输入文件中 ipot=3。','Ziegler–Biersack–Littmark universal screened collision potential; ipot=3.'),
        (4,'Nakagawa–Yamamura','Nakagawa–Yamamura','本机内核的 Nakagawa–Yamamura 势分支；需要相容的积分设置，不支持 iintegral=0。','Local Nakagawa–Yamamura potential branch. Requires compatible integration settings; iintegral=0 is unsupported.'),
        (5,'Si 专用势','Si potential','本机 Si 势分支；核对材料适用性与积分方式，不支持 iintegral=0。不是任意材料的默认势。','Local Si potential branch. Check material applicability and integration settings; iintegral=0 is unsupported. Not a general default.'),
    ),
    'isbv': (
        (1,'各元素固定值','Fixed per element','控制原子离开表面时采用的结合能规则，不是能量数值（eV）。模型 1 使用各元素自身的 e_surfb，来自材料表或输入覆盖。','Selects the surface escape binding-energy rule, not an energy value in eV. Model 1 uses each species own e_surfb, from material tables or input overrides.'),
        (2,'表面成分混合','Surface composition mix','按表面成分混合结合能：元素对矩阵项取表面组分的 e_surfb；任一项结合能近零时该元素对项为零。','Mixes binding energies using surface composition. Pair matrix entries use the surface partner e_surfb; an entry is zero if either binding energy is near zero.'),
        (3,'元素对平均','Pair average','元素对结合能取两者 e_surfb 的算术平均，再参与表面成分加权；任一项近零时对应元素对项为零。','Pair binding energies use the arithmetic mean of the two e_surfb values, followed by surface-composition weighting. A pair is zero if either value is near zero.'),
        (4,'化合物模型','Compound model','化合物专用分支：表面项沿用元素自身结合能，材料表还会用化合物生成焓修正体结合能。需相应化合物数据。','Compound branch: surface terms retain element self values, while compound formation enthalpy modifies bulk binding in the material-table logic. Requires suitable compound data.'),
        (6,'自定义结合能矩阵','Custom binding matrix','从 mat_surfb.inp 读取元素对表面结合能矩阵；文件须与组分数和顺序一致。能量单位 eV。','Reads the surface-binding matrix from mat_surfb.inp. Supply a file matching the species count and order. Energies are in eV.'),
        (7,'对角矩阵（高级）','Diagonal matrix (advanced)','本机高级分支：初始结合能矩阵仅对角项为 e_surfb，非对角项为零。请按研究模型核对适用性。','Advanced local branch: the initial binding matrix has e_surfb only on its diagonal and zero off-diagonal entries. Check applicability to the intended model.'),
        (8,'table1a 化合物修正','table1a compound model','本机使用 table1a 的特殊分支，重新设置表面结合能和截止能，并包含化合物相关处理；使用前核对材料表与参数。','Special local table1a branch resets surface binding and cutoff energies and includes compound handling. Check the material table and parameters before use.'),
    ),
    'case_e0': (
        (0, '固定能量', 'Fixed energy',
         '使用各入射组分的 e0_beam 作为固定能量，单位 eV。',
         'Use e0_beam as the fixed energy for each incident species, in eV.'),
        (1, '能量文件', 'Energy file',
         '从 energy.inp 读取并抽样能量分布；不是固定能量。能量单位为 eV。',
         'Read and sample the energy distribution from energy.inp. Energy is in eV.'),
        (2, '三维麦克斯韦', '3D Maxwellian',
         '三维麦克斯韦热运动，加上鞘层加速（charge × shth）。e0_beam 是温度能量尺度 kT（eV），不是固定粒子能量。本模式会重新计算入射方向，不能与角度模式完全独立理解。',
         '3D Maxwellian thermal motion with sheath acceleration (charge × shth). e0_beam is the temperature energy scale kT (eV), not a fixed particle energy. This mode recalculates direction and is not independent of the angular mode.'),
        (3, '简化麦克斯韦', 'Reduced Maxwellian',
         '简化麦克斯韦模式，调用 energ；本机实现的入射方向限制在 x–z 平面。e0_beam 是温度能量尺度 kT（eV），并考虑鞘层加速；本模式会重新计算方向。',
         'Reduced Maxwellian mode using energ; this local implementation restricts directions to the x–z plane. e0_beam is the temperature energy scale kT (eV), with sheath acceleration. This mode recalculates direction.'),
        (5, '高斯能量', 'Gaussian energy',
         '高斯能量分布：中心为 e0_beam，标准差为 de0_beam，单位 eV。本机内核在中心 ±4σ 内抽样，并排除负能量；de0_beam 需为正。',
         'Gaussian energy: center e0_beam, standard deviation de0_beam, in eV. The local engine samples within ±4σ and rejects negative energies; de0_beam must be positive.'),
    ),
    'case_alpha': (
        (0, '固定角度', 'Fixed angle',
         '使用各入射组分的 alpha0 作为固定入射角，单位为度；相对参考表面法线，0° 为垂直入射。能量模式 2/3 会重新计算方向。',
         'Use alpha0 as the fixed angle for each incident species, in degrees from the reference surface normal; 0° is normal incidence. Energy modes 2/3 recalculate direction.'),
        (1, '极角均匀', 'Uniform polar angle',
         '极角在 0～alpha0 之间均匀抽样，方位角随机。alpha0 为角度上限（度），不是分布中心；这不是立体角均匀分布。',
         'Sample the polar angle uniformly from 0 to alpha0 with random azimuth. alpha0 is the upper bound in degrees, not the center. This is not uniform sampling over solid angle.'),
        (2, '余弦通量', 'Cosine flux',
         '内置余弦通量分布：极角为 0～90°，方位角随机。按极角统计时，概率密度在 45° 附近最大；不由 alpha0 指定中心。',
         'Built-in cosine-flux distribution over polar angles 0–90°, with random azimuth. The polar-angle density peaks near 45°; alpha0 does not set its center.'),
        (3, '小角偏重', 'Small-angle weighted',
         '内置小角度偏重分布：极角为 0～90°，方位角随机，靠近法线的小角度较多；与模式 2 的余弦通量分布不同。',
         'Built-in small-angle-weighted distribution over 0–90°, with random azimuth. Angles near the normal are more frequent; this differs from the cosine-flux distribution in mode 2.'),
        (4, '角度文件', 'Angle file',
         '从 angle.inp 读取角度分布，角度单位为度。注意：本机源码抽样 alpha_pol 后，坐标转换却使用 alpha_z，疑似变量错误；尚未专项数值验证或修复，使用前需核实。',
         'Read the angular distribution from angle.inp, in degrees. Caution: the local source samples alpha_pol but uses alpha_z in the coordinate conversion. This suspected variable error has not been numerically verified or fixed; verify before use.'),
        (5, '高斯角度', 'Gaussian angle',
         '高斯角度分布：中心为 alpha0，标准差为 dalpha0，单位为度。本机在中心 ±4σ 内抽样，并限制到 −180～180°；dalpha0 需为正。',
         'Gaussian angle: center alpha0, standard deviation dalpha0, in degrees. The local engine samples within ±4σ and restricts angles to −180–180°; dalpha0 must be positive.'),
    ),
    'case_geo': (
        (26, '基底＋矩形块', 'Substrate + blocks',
         '平面基底加 fig.inp 中的矩形材料块；基底由 geo_x、geo_z 和基底成分定义。当前画笔、矩形等几何工具主要服务于此模式。输入长度始终为 Å。',
         'Flat substrate plus rectangular material blocks from fig.inp. geo_x, geo_z and substrate fractions define the substrate. Current brush/rectangle tools mainly serve this mode. Input lengths always use Å.'),
        (20, '二维平面', '2D flat',
         '二维平面靶：总宽为 2 × geo_x，平面上表面参考高度为 z=0，底部为 geo_z（负值）。输入长度始终为 Å。',
         '2D flat target: full width 2 × geo_x, reference top surface z=0, bottom geo_z (negative). Input lengths always use Å.'),
        (24, '轮廓（左起）', 'Profile (left origin)',
         '从 rauh.inp 读取上表面折线；x 从左边界起算，通常覆盖 0～2 × geo_x，内核再转成中心坐标。点按 x 递增，相邻点线性插值。底部仍为 geo_z，成分取基底设置；pr_amp/pr_wl 可叠加余弦起伏。输入长度始终为 Å。',
         'Read the top-surface polyline from rauh.inp. File x starts at the left edge, usually 0 to 2 × geo_x, then shifts to centered coordinates. Use increasing x; adjacent points are linearly interpolated. Bottom remains geo_z and composition uses substrate settings; pr_amp/pr_wl may add cosine modulation. Input lengths always use Å.'),
        (25, '轮廓（中心）', 'Profile (centered)',
         '从 rauh.inp 读取上表面折线；x 直接采用以靶中心为零的坐标，通常覆盖 −geo_x～+geo_x。点按 x 递增，相邻点线性插值。底部仍为 geo_z，成分取基底设置；pr_amp/pr_wl 可叠加余弦起伏。输入长度始终为 Å。',
         'Read the top-surface polyline from rauh.inp using x centered on the target, usually −geo_x to +geo_x. Use increasing x; adjacent points are linearly interpolated. Bottom remains geo_z and composition uses substrate settings; pr_amp/pr_wl may add cosine modulation. Input lengths always use Å.'),
        (27, '余弦表面', 'Cosine surface',
         '由 pr_amp 和 pr_wl 定义余弦起伏：z(x)=pr_amp × [1−cos(2πx/pr_wl)]；pr_amp 为公式振幅系数，峰谷差为 2 × pr_amp，pr_wl 为波长。底部由 geo_z 定义，输入长度始终为 Å。',
         'Cosine surface: z(x)=pr_amp × [1−cos(2πx/pr_wl)]. pr_amp is the formula coefficient, with peak-to-valley height 2 × pr_amp; pr_wl is the wavelength. geo_z defines the bottom. Input lengths always use Å.'),
        (10, '一维平面', '1D flat',
         '一维平面靶，沿深度描述靶材；不用于二维矩形凸起结构。基底参数及组分仍来自 tri.inp，输入长度始终为 Å。',
         '1D flat target described along depth; not for 2D rectangular protrusions. Substrate parameters and composition remain in tri.inp. Input lengths always use Å.'),
    ),
}


class ModeComboBox(NoWheelComboBox):
    """闭合框和展开菜单均支持 500 ms 悬停；移动到新项重新计时。"""
    def __init__(self, key, parent=None):
        super().__init__(parent)
        self.mode_key = key
        self._language = 'zh'
        self._hover_index = -1
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(500)
        self._hover_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._hover_timer.timeout.connect(self._show_hover_tip)
        self.setProperty('tooltipDelayMs', 500)
        view = self.view()
        self._popup_view = view
        self._popup_viewport = view.viewport()
        view.setProperty('tooltipDelayMs', 500)
        view.viewport().setProperty('tooltipDelayMs', 500)
        view.setMouseTracking(True)
        view.viewport().setMouseTracking(True)
        view.installEventFilter(self)
        view.viewport().installEventFilter(self)
        for value, zh, en, zh_tip, en_tip in MODE_OPTIONS[key]:
            self.addItem(f'{value} · {zh}', value)
        self.currentIndexChanged.connect(self._sync_tip)
        self.set_language('zh')

    def set_language(self, language):
        self._cancel_hover()
        self._language = language
        options = {row[0]: row for row in MODE_OPTIONS[self.mode_key]}
        blocked = self.blockSignals(True)
        try:
            for i in range(self.count()):
                row = options.get(self.itemData(i))
                if row is None:
                    if self.mode_key in ('ipot','isbv'):
                        value=self.itemData(i)
                        self.setItemText(i,f'{value} · '+('Preserved input (advanced)' if language=='en' else '保留输入（高级）'))
                        tip=('Original value retained without substitution. Verify support in the local engine before running.' if language=='en' else '保留原始编号，不自动替换。此编号不在常用选项中，运行前请核对本机内核支持情况。')
                        self.setItemData(i,tip,Qt.ItemDataRole.ToolTipRole)
                    continue
                en = language == 'en'
                self.setItemText(i, f'{row[0]} · {row[2 if en else 1]}')
                # 富文本使长说明自动换行，不横向铺满屏幕。
                tip = f'<qt><b>{self.mode_key} = {row[0]}</b><br/>{escape(row[4 if en else 3])}</qt>'
                self.setItemData(i, tip, Qt.ItemDataRole.ToolTipRole)
        finally:
            self.blockSignals(blocked)
        self._sync_tip()

    def _sync_tip(self, *args):
        self.setToolTip(self.currentData(Qt.ItemDataRole.ToolTipRole) or '')

    def _cancel_hover(self):
        self._hover_timer.stop()
        self._hover_index = -1
        QToolTip.hideText()

    def _queue_hover(self, index):
        if index == self._hover_index:
            return
        self._cancel_hover()
        self._hover_index = index
        if index >= 0:
            self._hover_timer.start()

    def _show_hover_tip(self):
        view = self.view()
        if not view.isVisible():
            return
        point = view.viewport().mapFromGlobal(QCursor.pos())
        index = view.indexAt(point)
        if index.isValid() and index.row() == self._hover_index:
            tip = self.itemData(index.row(), Qt.ItemDataRole.ToolTipRole)
            if tip:
                QToolTip.showText(QCursor.pos(), tip, view.viewport(), view.visualRect(index))

    def eventFilter(self, obj, event):
        # 父类初始化时已安装过滤器，此时计时器尚未创建。
        # 过滤器中不能调用 self.view()：Qt 首次创建菜单时会重入此处。
        if hasattr(self, '_popup_viewport') and obj in (self._popup_view, self._popup_viewport):
            kind = event.type()
            if kind == QEvent.Type.MouseMove and obj is self._popup_viewport:
                index = self._popup_view.indexAt(event.position().toPoint())
                self._queue_hover(index.row() if index.isValid() else -1)
            elif kind in (QEvent.Type.Leave, QEvent.Type.Hide, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel):
                self._cancel_hover()
            elif kind == QEvent.Type.ToolTip:
                # 展开列表由专用计时器控制，避免原生提示抢先显示。
                return True
        return super().eventFilter(obj, event)

    def hidePopup(self):
        self._cancel_hover()
        super().hidePopup()
