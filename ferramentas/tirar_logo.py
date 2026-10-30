"""Apaga a logo de uma foto de peça clara, preenchendo com o tecido em volta.

Uso:  python ferramentas/tirar_logo.py entrada.jpg saida.jpg x0 y0 x1 y1
Ex.:  python ferramentas/tirar_logo.py assets/produtos/_moletom-original.jpg assets/produtos/_moletom-liso-original.jpg 1060 570 1335 735

x0 y0 x1 y1 é uma caixa (em pixels da foto) com a logo inteira e um pouco de tecido em volta.
Só o que é mais escuro que o tecido dentro da caixa é apagado, então dá para usar uma caixa folgada
(diferente do gerar_cores.py, que acha a logo sozinho e pode confundir com sombras da peça).
"""
import sys

import numpy as np
from PIL import Image


def dilatar(m, raio):
    out = m.copy()
    for eixo in (0, 1):
        base = out.copy()
        for s in range(1, raio + 1):
            out = out | np.roll(base, s, eixo) | np.roll(base, -s, eixo)
    return out


def tirar_logo(entrada, saida, caixa):
    px = np.asarray(Image.open(entrada).convert("RGB"), dtype=np.float32) / 255
    x0, y0, x1, y1 = caixa
    reg = px[y0:y1, x0:x1].copy()
    lum = 0.299 * reg[..., 0] + 0.587 * reg[..., 1] + 0.114 * reg[..., 2]
    tecido = np.median(lum)
    # a logo e a borda suave dela: tudo um pouco mais escuro que o tecido
    m = dilatar(lum < tecido - 0.06, 4)
    m[[0, -1], :] = False
    m[:, [0, -1]] = False
    reg[m] = reg[~m].mean(axis=0)
    # espalha o tecido de fora para dentro até assentar
    for _ in range(1500):
        media = (np.roll(reg, 1, 0) + np.roll(reg, -1, 0) + np.roll(reg, 1, 1) + np.roll(reg, -1, 1)) / 4
        reg[m] = media[m]
    # granulação parecida com a do tecido, para não ficar borrado
    rng = np.random.default_rng(7)
    reg[m] += rng.normal(0, lum[~m].std() * 0.6, reg[m].shape)
    px[y0:y1, x0:x1] = reg
    Image.fromarray((np.clip(px, 0, 1) * 255).round().astype(np.uint8)).save(saida, quality=95)
    print(saida, "apagados", int(m.sum()), "pixels")


if __name__ == "__main__":
    a = sys.argv[1:]
    tirar_logo(a[0], a[1], tuple(int(v) for v in a[2:6]))
