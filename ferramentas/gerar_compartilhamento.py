"""Gera a imagem de prévia do link (WhatsApp, Instagram, Facebook) e os ícones da aba.

Saída em assets/:
  compartilhar.jpg   1200x630, aparece quando alguém compartilha o site
  icone-32.png       ícone da aba do navegador
  icone-180.png      ícone ao salvar o site na tela inicial do celular

Uso:  python ferramentas/gerar_compartilhamento.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
FONTES = Path("C:/Windows/Fonts")

TINTA = (4, 6, 12)
AZUL = (31, 107, 255)
AZUL_CLARO = (91, 147, 255)
CINZA = (175, 186, 210)


def fonte(nome, tam):
    try:
        return ImageFont.truetype(str(FONTES / nome), tam)
    except OSError:
        return ImageFont.load_default()


def fundo(w, h):
    """Preto com o brilho azul diagonal do site."""
    img = Image.new("RGB", (w, h), TINTA)
    luz = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(luz)
    d.polygon([(w * 0.30, 0), (w * 0.42, 0), (w * 0.12, h), (w * 0.00, h)], fill=110)
    d.polygon([(w * 0.50, 0), (w * 0.55, 0), (w * 0.25, h), (w * 0.20, h)], fill=50)
    luz = luz.filter(ImageFilter.GaussianBlur(40))
    img.paste(Image.new("RGB", (w, h), AZUL), (0, 0), luz)
    return img


def cantos(img, raio):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], raio, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def quadrado(caminho, lado):
    """Corte quadrado no centro da foto do produto."""
    im = Image.open(caminho).convert("RGB")
    s = min(im.size)
    x, y = (im.width - s) // 2, (im.height - s) // 2
    return im.crop((x, y, x + s, y + s)).resize((lado, lado), Image.LANCZOS)


def compartilhar():
    w, h = 1200, 630
    img = fundo(w, h)

    # fotos à direita: camisa em cima, polo e copo embaixo
    lado = 250
    fotos = [("camisa.jpg", (650, 50)), ("moletom-preto.jpg", (920, 50)),
             ("polo.jpg", (650, 330)), ("copo.jpg", (920, 330))]
    for nome, pos in fotos:
        q = cantos(quadrado(ASSETS / "produtos" / nome, lado), 22)
        img.paste(q, pos, q)

    # logo e textos à esquerda
    logo = Image.open(ASSETS / "logo-ponto-nobre.png").convert("RGBA")
    lw = 520
    logo = logo.resize((lw, round(lw * logo.height / logo.width)), Image.LANCZOS)
    img.paste(logo, (60, 70), logo)

    d = ImageDraw.Draw(img)
    d.text((64, 340), "Uniformes e brindes", font=fonte("segoeuib.ttf", 44), fill=(238, 242, 251))
    d.text((64, 392), "com a logo da sua empresa", font=fonte("segoeuib.ttf", 44), fill=AZUL_CLARO)
    d.text((64, 462), "Bordado · Gravação a laser · Impressão 3D", font=fonte("segoeui.ttf", 27), fill=CINZA)

    # selo do orçamento
    selo = "Orçamento pelo WhatsApp"
    f = fonte("segoeuib.ttf", 26)
    tw = d.textlength(selo, font=f)
    d.rounded_rectangle([64, 524, 64 + tw + 48, 578], 27, fill=AZUL)
    d.text((88, 532), selo, font=f, fill=(255, 255, 255))

    img.save(ASSETS / "compartilhar.jpg", quality=86, optimize=True, progressive=True)


def asas_brilhantes():
    """As asas da logo original em alta resolução, quase brancas e com fundo transparente."""
    im = Image.open(ASSETS / "logo-original.png").convert("RGB").crop((380, 40, 1230, 335))
    px = np.asarray(im, dtype=np.float32) / 255
    lum = px.max(axis=2)
    alfa = np.clip((lum - 0.06) / 0.18, 0, 1)                 # o preto do fundo some
    tom = 0.62 + 0.38 * np.clip((lum - 0.25) / 0.6, 0, 1)      # prata clara, mantendo o relevo das penas
    rgb = np.stack([tom, tom, np.clip(tom * 1.03, 0, 1)], axis=-1)
    return Image.fromarray((np.dstack([rgb, alfa]) * 255).astype(np.uint8), "RGBA")


def icones():
    asas = asas_brilhantes()
    for lado in (32, 48, 180, 512):
        g = lado * 8                                           # desenha grande e reduz, para ficar nítido
        base = Image.new("RGBA", (g, g), (0, 0, 0, 0))
        fundo = Image.new("RGBA", (g, g), (0, 0, 0, 0))
        y = np.linspace(0, 1, g)[:, None]
        cor = (np.array([24, 42, 82]) * (1 - y) + np.array([9, 16, 32]) * y).astype(np.uint8)   # marinho
        fundo = Image.fromarray(np.repeat(cor[:, None, :], g, axis=1).reshape(g, g, 3)).convert("RGBA")
        mascara = Image.new("L", (g, g), 0)
        ImageDraw.Draw(mascara).rounded_rectangle([0, 0, g - 1, g - 1], round(g * 0.22), fill=255)
        base.paste(fundo, (0, 0), mascara)
        aw = round(g * (0.98 if lado <= 48 else 0.82))
        a = asas.resize((aw, round(aw * asas.height / asas.width)), Image.LANCZOS)
        if lado <= 48:                                         # nos tamanhos pequenos, engrossa um pouco o traço
            a.putalpha(a.getchannel("A").filter(ImageFilter.MaxFilter(2 * (g // 64) + 1)))
        base.paste(a, ((g - a.width) // 2, (g - a.height) // 2), a)
        base.resize((lado, lado), Image.LANCZOS).save(ASSETS / f"icone-{lado}.png", optimize=True)


if __name__ == "__main__":
    compartilhar()
    icones()
    for n in ("compartilhar.jpg", "icone-32.png", "icone-48.png", "icone-180.png", "icone-512.png"):
        print(n, (ASSETS / n).stat().st_size // 1024, "KB")
