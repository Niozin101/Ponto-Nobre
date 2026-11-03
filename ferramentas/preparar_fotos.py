"""Coloca fotos novas no padrão do site: 1200x900, peça centralizada e fundo azul igual ao das outras fotos.

Uso:  python ferramentas/preparar_fotos.py entrada.jpg saida.jpg [--logo x y largura]
Ex.:  python ferramentas/preparar_fotos.py assets/produtos/_trico-frente-original.jpg assets/produtos/trico-liso.jpg
      python ferramentas/preparar_fotos.py assets/produtos/_trico-frente-original.jpg assets/produtos/trico.jpg --logo 53.6 22.5 10.1

      python ferramentas/preparar_fotos.py assets/produtos/_jaqueta-original.jpg assets/produtos/jaqueta.jpg --escura
      python ferramentas/preparar_fotos.py assets/produtos/_moletom-original.jpg assets/produtos/moletom.jpg --mascara-de assets/produtos/_moletom-liso-original.jpg

--logo borda a logo Ponto Nobre em preto, como nas outras fotos (posição e largura em % da foto).
--mascara-de recorta a peça usando outra foto do mesmo tamanho (a versão sem logo, de tirar_logo.py),
  para manter a logo que já veio na foto.
--escura recorta peça escura (ex.: jaqueta preta) que já veio sobre fundo azul.
Serve para peças claras sobre fundo liso (o fundo original é trocado pelo azul).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LARGURA, ALTURA = 1200, 900
ALTURA_PECA = 790
CENTRO = np.array([52, 76, 101], dtype=np.float32) / 255     # azul do meio das outras fotos
BORDA = np.array([44, 65, 89], dtype=np.float32) / 255       # azul dos cantos
LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo-ponto-nobre.png"


def fundo_azul():
    y, x = np.mgrid[0:ALTURA, 0:LARGURA].astype(np.float32)
    d = np.sqrt(((x - LARGURA / 2) / (LARGURA * 0.62)) ** 2 + ((y - ALTURA * 0.45) / (ALTURA * 0.75)) ** 2)
    t = np.clip(d, 0, 1)[..., None]
    img = CENTRO * (1 - t) + BORDA * t
    ruido = np.random.default_rng(3).normal(0, 0.006, img.shape)   # leve textura de papel
    return np.clip(img + ruido, 0, 1)


def logo_bordada(largura_px):
    """A logo Ponto Nobre em preto, com o relevo da linha (a versão prata vira tons de preto)."""
    lg = Image.open(LOGO).convert("RGBA")
    lg = lg.resize((largura_px, round(largura_px * lg.height / lg.width)), Image.LANCZOS)
    px = np.asarray(lg, dtype=np.float32) / 255
    lum = 0.299 * px[..., 0] + 0.587 * px[..., 1] + 0.114 * px[..., 2]
    tom = np.clip(0.05 + (lum - 0.45) * 0.28, 0.04, 0.22)
    rgb = np.stack([tom, tom, tom * 1.04], axis=-1)
    out = np.dstack([rgb, px[..., 3]])
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA")


def buracos(m):
    """Partes da máscara que não são peça mas ficam presas dentro dela (255 nos buracos, 0 no resto)."""
    b = Image.new("L", (m.width + 2, m.height + 2), 0)
    b.paste(m.point(lambda v: 255 if v > 20 else 0), (1, 1))
    ImageDraw.floodfill(b, (0, 0), 128)            # o fundo de verdade encosta na borda
    return np.where(np.asarray(b)[1:-1, 1:-1] == 0, 255, 0).astype(np.uint8)


def preparar(entrada, saida, logo=None, mascara_de=None, escura=False):
    im = Image.open(entrada).convert("RGB")
    # recorte calculado em outra foto do mesmo tamanho (a versão sem logo): a logo escura não vira fundo
    px = np.asarray(Image.open(mascara_de).convert("RGB") if mascara_de else im, dtype=np.float32) / 255
    lum = 0.299 * px[..., 0] + 0.587 * px[..., 1] + 0.114 * px[..., 2]

    if escura:
        # peça escura sobre fundo azul: o que não for azulado como o fundo (cor tirada dos cantos) é peça
        canto = np.concatenate([px[:20, :20], px[:20, -20:], px[-20:, :20], px[-20:, -20:]]).reshape(-1, 3).mean(0)
        dist = np.sqrt(((px - canto) ** 2).sum(-1))
        alfa = np.clip((dist - 0.06) / 0.08, 0, 1)
    else:
        # peça = tudo bem mais claro que o fundo; só suaviza a borda
        alfa = np.clip((lum - 0.45) / 0.15, 0, 1)
    m = Image.fromarray((alfa * 255).astype(np.uint8))
    m = m.filter(ImageFilter.GaussianBlur(0.8))   # sem "fechar" a máscara: o vão entre manga e corpo continua sendo fundo
    # sombras escuras cercadas pela peça (ex.: dentro do capuz) são peça: só é fundo o que chega até a borda da foto
    m = Image.fromarray(np.maximum(np.asarray(m), buracos(m)))

    # recorta só a peça e redimensiona para a altura padrão
    caixa = m.point(lambda v: 255 if v > 20 else 0).getbbox()
    peca = im.crop(caixa)
    mascara = m.crop(caixa)
    # peça com os braços abertos pode ser mais larga que a foto: aí ela diminui para caber com folga
    k = min(ALTURA_PECA / peca.height, (LARGURA - 70) / peca.width)
    tam = (round(peca.width * k), round(peca.height * k))
    peca = peca.resize(tam, Image.LANCZOS)
    mascara = mascara.resize(tam, Image.LANCZOS)

    base = Image.fromarray((fundo_azul() * 255).astype(np.uint8))
    x, y = (LARGURA - tam[0]) // 2, (ALTURA - tam[1]) // 2

    # sombra suave e curta em volta, como nas outras fotos
    sombra = Image.new("L", (LARGURA, ALTURA), 0)
    sombra.paste(mascara, (x, y + 5))
    sombra = sombra.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.30))
    base.paste(Image.new("RGB", base.size, (14, 26, 48)), (0, 0), sombra)

    base.paste(peca, (x, y), mascara)

    if logo:
        lx, ly, lw = logo
        bordado = logo_bordada(round(LARGURA * lw / 100))
        base.paste(bordado, (round(LARGURA * lx / 100), round(ALTURA * ly / 100)), bordado)

    base.save(saida, quality=86, optimize=True, progressive=True)
    print(saida, base.size, "peça em", (x, y, x + tam[0], y + tam[1]))


if __name__ == "__main__":
    args = sys.argv[1:]
    logo = mascara_de = None
    escura = "--escura" in args
    args = [a for a in args if a != "--escura"]
    if "--logo" in args:
        i = args.index("--logo")
        logo = tuple(float(v) for v in args[i + 1:i + 4])
        args = args[:i] + args[i + 4:]
    if "--mascara-de" in args:
        i = args.index("--mascara-de")
        mascara_de = args[i + 1]
        args = args[:i] + args[i + 2:]
    preparar(args[0], args[1], logo, mascara_de, escura)
