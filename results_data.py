# Adapted from SDtrimspplot helpers/sdtrimsp_2d.py; see PLOTTER-LICENSE.txt.
"""Local SDTrimSP-2D reader, verified against the supplied 3.01 package.

Keep geometry, fluence, component order and the code's global normalization.
No interpolation, smoothing, or renormalization is applied to raw results.
"""
from pathlib import Path
import re

import numpy as np
import pandas as pd




def _numbers(text, start=0):
    rows = []
    for number, line in enumerate(text.splitlines()[start:], start + 1):
        line = line.split('#', 1)[0].split('!', 1)[0].strip()
        if not line:
            continue
        tokens = line.split()
        tag = 'sum' if tokens[-1].lower() == 'sum' else ''
        if tag:
            tokens.pop()
        try:
            values = [float(x.replace('D', 'E').replace('d', 'e')) for x in tokens]
        except ValueError as exc:
            raise ValueError(f'第 {number} 行含有无法解析的数值。') from exc
        if not np.isfinite(values).all():
            raise ValueError(f'第 {number} 行含 NaN 或无穷值。')
        rows.append((number, values, tag))
    return rows


def _integer(value, name):
    if value < 0 or not float(value).is_integer():
        raise ValueError(f'{name} 必须是非负整数。')
    return int(value)


def _unique_symbols(symbols):
    result, seen = [], {}
    for symbol in symbols:
        seen[symbol] = seen.get(symbol, 0) + 1
        result.append(symbol if seen[symbol] == 1 else f'{symbol}#{seen[symbol]}')
    return result


def parse_cells(text, *, invalid_snapshots=None):
    lines = text.splitlines()
    symbol_line = next((i for i, line in enumerate(lines)
                        if line.lstrip().startswith('# symbol')), None)
    start = next((i for i, line in enumerate(lines) if '#cel_coord' in line), None)
    if symbol_line is None or start is None or symbol_line + 1 >= len(lines):
        raise ValueError('不是受支持的 T_10_2D.dat：缺少组成或单元坐标表头。')
    symbols = _unique_symbols(lines[symbol_line + 1].split())
    if not symbols:
        raise ValueError('没有找到组分名称。')
    columns = ['x1_A', 'x2_A', 'z1_A', 'z2_A'] + [f'fraction_{s}' for s in symbols]
    columns += ['density_at_A3', 'cell_id']
    rows, snapshots, i = _numbers(text, start + 1), [], 0
    while i < len(rows):
        line, header, tag = rows[i]
        if len(header) != 5 or tag:
            raise ValueError(f'第 {line} 行不是二维单元数据块头。')
        count = _integer(header[1], '单元数')
        history = _integer(header[2], '历史步')
        block = rows[i + 1:i + 1 + count]
        if len(block) != count or any(len(row) != len(columns) or tag for _, row, tag in block):
            raise ValueError(f'历史步 {history} 的单元数据不完整或列数与组分不一致。')
        df = pd.DataFrame([row for _, row, _ in block], columns=columns)
        if count:
            if (df.density_at_A3 < 0).any():
                raise ValueError(f'历史步 {history} 存在负原子数密度。')
            ids = df.cell_id.to_numpy()
            if (ids != np.floor(ids)).any() or df.cell_id.duplicated().any():
                raise ValueError(f'历史步 {history} 的单元编号无效或重复。')
            if ((df.x2_A <= df.x1_A) | (df.z2_A <= df.z1_A)).any():
                if invalid_snapshots is None:
                    raise ValueError(f'历史步 {history} 存在无效的单元边界。')
                # Reject the entire snapshot, never silently remove or enlarge cells.
                invalid_snapshots.append({'history':history,'fluence':header[0],
                    'invalid_cells':int(((df.x2_A <= df.x1_A) | (df.z2_A <= df.z1_A)).sum())})
                i += count + 1
                continue
            df['cell_id'] = df.cell_id.astype(int)
        snapshots.append({'fluence': header[0], 'history': history, 'data': df})
        i += count + 1
    if not snapshots and not invalid_snapshots:
        raise ValueError('没有找到完整的二维单元数据块。')
    return symbols, snapshots


def parse_curves(text, kind, symbols=None):
    if kind not in ('surface', 'yield'):
        raise ValueError('未知的二维曲线类型。')
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith('#nr-cell')), None)
    if start is None:
        raise ValueError('缺少 #nr-cell 数据块头。')
    rows, snapshots, i = _numbers(text, start + 1), [], 0
    while i < len(rows):
        line, header, tag = rows[i]
        if len(header) != 4 or tag:
            raise ValueError(f'第 {line} 行不是二维曲线数据块头。')
        count, history = _integer(header[0], '记录数'), _integer(header[1], '历史步')
        block = rows[i + 1:i + 1 + count]
        if len(block) != count:
            raise ValueError(f'历史步 {history} 的曲线数据不完整。')
        if kind == 'surface':
            columns = ['x_A', 'z_A', 'cell_id']
        else:
            ncols = len(block[0][1]) if block else (1 + 2 * len(symbols or []))
            if ncols < 3 or ncols % 2 != 1:
                raise ValueError('局部反射与溅射贡献 的列数无效。')
            ncp = (ncols - 1) // 2
            if symbols and len(symbols) != ncp:
                raise ValueError('局部反射与溅射贡献 的组分数与 T_10_2D.dat 不一致，请使用同一算例文件。')
            labels = symbols or [f'组分{k + 1}' for k in range(ncp)]
            columns = ['x_A'] + [f'R_{s}' for s in labels] + [f'Y_{s}' for s in labels]
        if any(len(row) != len(columns) or tag for _, row, tag in block):
            raise ValueError(f'历史步 {history} 的曲线列数错误。')
        df = pd.DataFrame([row for _, row, _ in block], columns=columns)
        snap = {'fluence': header[3], 'history': history, 'data': df}
        i += count + 1
        if kind == 'yield' and i < len(rows) and rows[i][2] == 'sum':
            summary = rows[i][1]
            if len(summary) != len(columns):
                raise ValueError('局部反射与溅射贡献 的 sum 行列数错误。')
            calculated = df.iloc[:, 1:].sum().to_numpy()
            if not np.allclose(calculated, summary[1:], rtol=2e-6, atol=2e-8):
                raise ValueError('局部贡献之和与文件的 sum 行不符。')
            snap['summary'] = dict(zip(columns[1:], summary[1:]))
            i += 1
        snapshots.append(snap)
    if not snapshots:
        raise ValueError('没有找到完整的二维曲线数据块。')
    return snapshots


def load_dataset(contents):
    recognized = {}
    for name, text in contents.items():
        if '#cel_coord' in text:
            kind = 'cells'
        elif '#surface coordinates: x z cell-Nr' in text:
            kind = 'surface'
        elif 'local R' in text and 'local Y' in text:
            kind = 'yield'
        else:
            continue
        if kind in recognized:
            raise ValueError('每种输出请只上传一份文件；请勿混合不同算例。')
        recognized[kind] = (name, text)
    if not recognized:
        raise ValueError('未识别到二维单元、表面或局部反射与溅射贡献 文件。请上传 T_10_2D.dat、surf.dat 或 sputter_yield.dat。')
    result = {'symbols': [], 'files': {k: v[0] for k, v in recognized.items()}, 'ignored': [],
              'invalid_cell_snapshots':[]}
    if 'cells' in recognized:
        result['symbols'], result['cells'] = parse_cells(recognized['cells'][1],
            invalid_snapshots=result['invalid_cell_snapshots'])
        if not result['cells']:result['files'].pop('cells',None)
    for kind in ('surface', 'yield'):
        if kind in recognized:
            result[kind] = parse_curves(recognized[kind][1], kind, result['symbols'])
    result['ignored'] = [n for n in contents if n not in result['files'].values()]
    return result


def cell_snapshot_warning(dataset,english=False):
    invalid=dataset.get('invalid_cell_snapshots',[])
    if not invalid:return ''
    steps=', '.join(str(s['history']) for s in invalid)
    if english:
        return ('T_10_2D.dat: invalid cell boundaries at histories '+steps+
                '. These entire snapshots are unavailable for cell plots, inventory and morphology; '
                'other valid histories and independent files remain available. No cells were repaired or removed from a retained snapshot.')
    return ('T_10_2D.dat：历史步 '+steps+
            ' 存在无效单元边界；这些整步不用于单元图、库存量或形貌分析。其他正常历史步及独立文件仍可查看，未补造边界或删减正常历史步中的单元。')


def cell_grid(snapshot, values, max_bins=1500000):
    """Preserve exact printed rectangular boundaries, including deformed z grids."""
    df = snapshot['data']
    if df.empty:
        raise ValueError('该历史步没有单元。')
    x = np.unique(df[['x1_A', 'x2_A']].to_numpy())
    z = np.unique(df[['z1_A', 'z2_A']].to_numpy())
    if (len(x) - 1) * (len(z) - 1) > max_bins:
        raise ValueError('精确边界组合过大，当前界面不进行重采样。请先导出 CSV，或使用更小的几何算例。')
    grid = np.full((len(z) - 1, len(x) - 1), np.nan)
    for row, value in zip(df.itertuples(index=False), values):
        if row.density_at_A3 <= 0:
            continue
        a, b = np.searchsorted(x, [row.x1_A, row.x2_A])
        c, d = np.searchsorted(z, [row.z1_A, row.z2_A])
        if np.isfinite(grid[c:d, a:b]).any():
            raise ValueError('检测到相互重叠的二维单元，请检查输出。')
        grid[c:d, a:b] = value
    return x, z, grid


