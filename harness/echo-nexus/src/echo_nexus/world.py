"""Operator-only coordinates and orientation; never sent to an agent."""
from rich.text import Text
from rich.style import Style
from .visual import PALETTE, grid_text


def arrow(vector):
    return {(1, 0): '→', (-1, 0): '←', (0, 1): '↓', (0, -1): '↑'}.get(tuple(vector[:2]), '◆')


def world_text(grid, width, height, observer=None, coordinates=True, focus=None):
    observer = observer or {}
    grid_text(grid, 1, 1)  # Validate dimensions even when rendering the coordinate viewport.
    if not coordinates:
        out = grid_text(grid, width, max(1, height - 2))
    else:
        # A coordinate viewport keeps one grid cell per tile; no invented interpolation.
        h, w = len(grid), len(grid[0])
        digits = max(2, len(str(w - 1)))
        footer_rows = 4 if len(observer.get('world_position') or []) == 3 else 3
        cols, rows = min(w, max(1, (width - 5) // digits)), min(h, max(1, height - footer_rows))
        pos = focus or observer.get('position') or (0, 0)
        x0 = max(0, min(w - cols, int(pos[0]) - cols // 2))
        y0 = max(0, min(h - rows, int(pos[1]) - rows // 2))
        out = Text(' y/x ' + ''.join(f'{x:0{digits}}' for x in range(x0, x0 + cols)), style='#ac91ce')
        for y in range(y0, y0 + rows):
            out.append(f'\n{y:03}  ', style='#ac91ce')
            for x in range(x0, x0 + cols):
                color = PALETTE[int(grid[y][x]) % len(PALETTE)]
                is_actor = observer.get('position') == [x, y]
                glyph = arrow(observer.get('direction', [0, 0])) + ' ' if is_actor else '  '
                glyph = glyph.ljust(digits)
                out.append(glyph, Style(color='#08080c' if color in ('#ffffff', '#f4d858') else '#ffffff', bgcolor=color, bold=is_actor))
        out.append(f'\n{w}×{h} · /cell X Y', style='#ac91ce')
    compass = 'N↑ E→ S↓ O←'
    if observer.get('position') is not None:
        compass += ' · celda ' + str(observer['position'])
    if observer.get('direction') is not None:
        compass += '\n' + observer.get('direction_kind', 'dirección') + ' ' + arrow(observer['direction'])
    if len(observer.get('world_position') or []) == 3:
        compass += '\nXYZ ' + str(observer['world_position']) + ' · mirada ' + str(observer.get('world_direction'))
    out.append('\n' + compass, style='#cfb1ff')
    return out
