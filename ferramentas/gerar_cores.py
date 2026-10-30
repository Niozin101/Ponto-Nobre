"""Gera as fotos dos produtos em cada cor do catálogo.

Lê as fotos brancas em assets/produtos/<id>.jpg e cria:
  <id>-<cor>.jpg         a peça na cor, com a logo Ponto Nobre
  <id>-liso.jpg          a peça branca sem logo (para aplicar a logo do cliente)
  <id>-liso-<cor>.jpg    a peça na cor, sem logo
O fundo azul fica igual; a peça recebe a nova cor mantendo dobras e sombras.
Em peças escuras, a logo preta vira clara (como seria o bordado de verdade).
No fim, mostra a área da logo de cada foto (em %), usada no site em LOGO_AREA.

Uso:  python ferramentas/gerar_cores.py [ids...]   (ex.: moletom moletom-costas; sem ids gera tudo)
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PASTA = Path(__file__).resolve().parent.parent / "assets" / "produtos"

CORES = {
    "Preto": "#232427", "Cinza": "#8a8d93", "Azul": "#1a2752", "AzulClaro": "#1a2752",
    "Marinho": "#1a2752", "Vermelho": "#d0202a", "Verde": "#0f7a3d", "Rosa": "#ee8cc1", "Bege": "#e5d4b6",
}

# Cores de cada produto (Branco é a foto original)
PRODUTOS = {
    "camisa":  ["Preto", "Cinza", "Azul", "Vermelho", "Verde"],
    "polo":    ["Preto", "Cinza", "Azul", "Vermelho", "Verde"],
}

# Peças fotografadas sem logo (ex.: costas): só geram as cores, não precisam da versão "-liso"
PRODUTOS_SEM_LOGO = {
    "camisa-costas":  ["Preto", "Cinza", "Azul", "Vermelho", "Verde"],
    "polo-costas":    ["Preto", "Cinza", "Azul", "Vermelho", "Verde"],
    "sueter-costas":  ["Preto", "Cinza", "Marinho", "Vermelho", "Verde", "Bege"],
    "moletom-costas": ["Preto", "Cinza", "Marinho", "Vermelho", "Verde", ("Azul", "AzulClaro"), "Rosa", "Bege"],
    "trico-costas":   ["Preto", "Cinza", "Marinho", "Vermelho", "Verde", "Bege"],
    "babylook-costas": ["Preto", "Cinza", "Azul", "Vermelho", "Verde", "Rosa"],
}

# Peças em que a foto sem logo já existe (<id>-liso.jpg, feita por preparar_fotos.py, com tirar_logo.py se a
# foto veio com logo). A logo é o que a foto tem de mais escuro que a versão lisa.
PRODUTOS_COM_LISO = {
    "trico": ["Preto", "Cinza", "Marinho", "Vermelho", "Verde", "Bege"],
    "sueter":  ["Preto", "Cinza", "Marinho", "Vermelho", "Verde", "Bege"],
    "moletom": ["Preto", "Cinza", "Marinho", "Vermelho", "Verde", ("Azul", "AzulClaro"), "Rosa", "Bege"],
    "babylook": ["Preto", "Cinza", "Azul", "Vermelho", "Verde", "Rosa"],
}


def slug(nome):
    return nome.lower()


def rampa(x, a, b):
    """0 em a, 1 em b, linear no meio."""
    return np.clip((x - a) / (b - a), 0, 1)


def dilatar(mascara, raio):
    """Expande a máscara 'raio' pixels em cada direção."""
    out = mascara.copy()
    for eixo in (0, 1):
        base = out.copy()
        for s in range(1, raio + 1):
            out = np.maximum(out, np.maximum(np.roll(base, s, eixo), np.roll(base, -s, eixo)))
    return out


def presos(clara):
    """1 onde não é peça mas fica cercado por ela (buracos que não chegam na borda da foto)."""
    h, w = clara.shape
    b = Image.new("L", (w + 2, h + 2), 0)
    b.paste(Image.fromarray(np.where(clara > 0.08, 255, 0).astype(np.uint8)), (1, 1))
    ImageDraw.floodfill(b, (0, 0), 128)
    return (np.asarray(b)[1:-1, 1:-1] == 0).astype(np.float32)


def analisar(px):
    """Separa fundo, peça e logo de uma foto (valores de 0 a 1)."""
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # Peça = pixels neutros (sem o tom azul do fundo) e claros
    neutro = 1 - rampa(b - r, 0.10, 0.18)
    # o fundo nunca é claro: tudo que é bem claro é peça, mesmo com um leve tom frio
    clara = np.maximum(neutro * rampa(lum, 0.40, 0.55), rampa(lum, 0.55, 0.68))
    fundo = np.median(px[(neutro < 0.05) & (lum < 0.5)], axis=0)
    # Logo = pixels neutros bem escuros por dentro da peça (longe da borda e da sombra dela)
    solida = (clara > 0.5).astype(np.float32)
    fechada = 1 - dilatar(1 - dilatar(solida, 18), 18)   # fecha os buracos onde está a logo
    miolo = 1 - dilatar(1 - fechada, 8)                    # afasta da borda da peça
    forte = (neutro > 0.5) & (lum < 0.2) & (miolo > 0.5)
    caixa = np.zeros_like(lum)
    area = None
    ys, xs = np.nonzero(forte)
    if len(xs) > 50:
        # a logo é o ponto com mais pixels escuros juntos; ignora sombras soltas (ex.: capuz)
        h, w = lum.shape
        grade, _, _ = np.histogram2d(ys, xs, bins=[h // 40, w // 40], range=[[0, h], [0, w]])
        cy, cx = np.unravel_index(np.argmax(grade), grade.shape)
        cy, cx = cy * 40 + 20, cx * 40 + 20
        perto = (np.abs(xs - cx) < 170) & (np.abs(ys - cy) < 100)
        xs, ys = xs[perto], ys[perto]
        x0, x1 = np.percentile(xs, [1, 99]).astype(int)
        y0, y1 = np.percentile(ys, [1, 99]).astype(int)
        caixa[max(0, y0 - 25):y1 + 25, max(0, x0 - 15):x1 + 15] = 1
        area = (x0, max(0, y0 - 6), x1, y1 + 22)  # inclui a linha fina de texto embaixo
    # Dentro da caixa da logo o limite é mais folgado, para pegar o texto fino
    logo = neutro * (1 - rampa(lum, 0.38, 0.74)) * miolo * caixa
    # Peça inteira: parte clara + áreas neutras de sombra por dentro + o que fica preso dentro dela
    # (ex.: sombra azulada dentro do capuz); só é fundo o que chega até a borda da foto
    peca = np.maximum(np.maximum(clara, neutro * fechada), presos(clara))
    return {"lum": lum, "clara": clara, "fundo": fundo, "logo": logo, "peca": peca, "caixa": caixa, "area": area}


def apagar_logo(foto):
    """Remove a logo da foto, preenchendo com o tecido em volta."""
    px = np.asarray(foto, dtype=np.float32) / 255
    a = analisar(px)
    buraco = dilatar((a["logo"] > 0.05).astype(np.float32), 3) * a["caixa"] > 0.5
    ys, xs = np.nonzero(a["caixa"])
    y0, y1, x0, x1 = ys.min() - 10, ys.max() + 10, xs.min() - 10, xs.max() + 10
    reg = px[y0:y1, x0:x1].copy()
    m = buraco[y0:y1, x0:x1]
    reg[m] = reg[~m].mean(axis=0)
    # espalha o tecido de fora para dentro do buraco até assentar
    for _ in range(600):
        media = (np.roll(reg, 1, 0) + np.roll(reg, -1, 0) + np.roll(reg, 1, 1) + np.roll(reg, -1, 1)) / 4
        reg[m] = media[m]
    # um pouco de granulação para não parecer borrado
    rng = np.random.default_rng(7)
    reg[m] += rng.normal(0, 0.006, reg[m].shape)
    px[y0:y1, x0:x1] = reg
    liso = Image.fromarray((np.clip(px, 0, 1) * 255).round().astype(np.uint8))
    return liso, a["area"]


def logo_pela_diferenca(foto, liso):
    """Quanto de cada pixel é logo, comparando a foto com a versão lisa (0 = tecido, 1 = logo cheia)."""
    lum = lambda im: np.asarray(im.convert("L"), dtype=np.float32) / 255
    l_liso, l_foto = lum(liso), lum(foto)
    d = l_liso - l_foto
    return np.where(d > 0.03, np.clip(d / np.maximum(l_liso - 0.06, 0.1), 0, 1), 0)


def recolorir(foto, hexcor, sem_logo=False, logo=None):
    px = np.asarray(foto, dtype=np.float32) / 255
    a = analisar(px)
    lum, peca = a["lum"], a["peca"]
    if logo is None:
        logo = a["logo"]
    if sem_logo:
        logo = np.zeros_like(logo)   # foto sem logo: nada de escuro vira "logo"

    # Sombreado da peça em relação ao branco mais comum dela
    ref = np.percentile(lum[a["clara"] > 0.9], 90)
    sombra = np.clip(lum / ref, 0, 1.08)

    cor = np.array([int(hexcor[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255
    lum_cor = 0.299 * cor[0] + 0.587 * cor[1] + 0.114 * cor[2]
    detalhe = (sombra - 1)[..., None]
    if lum_cor < 0.2:
        # preto: só multiplicar apaga as dobras; aqui o relevo é somado à cor, como tecido preto de verdade
        tecido = cor * (0.55 + 0.45 * sombra[..., None]) + detalhe * 0.28 + np.clip(detalhe, 0, None) * 0.5
    else:
        tecido = cor * sombra[..., None] + detalhe * 0.35 * (1 - lum_cor)

    cor_logo = np.array([0.93, 0.93, 0.94]) if lum_cor < 0.45 else np.array([0.07, 0.07, 0.08])
    # mantém o desenho da logo: em peça clara usa o pixel original
    if lum_cor >= 0.45:
        cor_logo = px
    tecido = tecido * (1 - logo[..., None]) + cor_logo * logo[..., None]

    # Na borda, mistura a nova cor com o fundo (e não com o branco original), sem contorno claro
    al = peca[..., None]
    borda = (al > 0) & (al < 1)
    base = np.where(borda, a["fundo"], px)
    saida = base * (1 - al) + np.clip(tecido, 0, 1) * al
    return Image.fromarray((np.clip(saida, 0, 1) * 255).round().astype(np.uint8))


# Produtos pretos (foto original em preto, logo prateada) e a área da logo na foto de 1200 px
PRODUTOS_ESCUROS = {
    "mochila": {"cores": ["Cinza"], "logo": (572, 234, 860, 406)},
    # o copo é vendido só em preto: gera apenas a versão sem logo
    "copo":    {"cores": [], "logo": (478, 346, 746, 502)},
}


def analisar_escuro(px, caixa_logo):
    """Separa fundo, corpo preto e logo clara de uma foto de produto preto."""
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    neutro = 1 - rampa(b - r, 0.05, 0.11)
    # o JPEG guarda a cor em blocos; suaviza para a borda não sair em degraus
    neutro = np.asarray(Image.fromarray((neutro * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)),
                        dtype=np.float32) / 255
    neutro = rampa(neutro, 0.35, 0.75)
    escuro = neutro * (1 - rampa(lum, 0.24, 0.34))   # o aço inox (claro) fica de fora
    x0, y0, x1, y1 = caixa_logo
    caixa = np.zeros_like(lum)
    caixa[y0:y1, x0:x1] = 1
    caixa *= neutro          # a caixa nunca avança sobre o fundo azul
    logo = caixa * rampa(lum, 0.22, 0.40)
    corpo = np.maximum(escuro, caixa)
    fundo = np.median(px[(neutro < 0.05)], axis=0)
    return {"lum": lum, "escuro": escuro, "logo": logo, "corpo": corpo, "fundo": fundo}


def apagar_logo_escuro(foto, caixa_logo):
    px = np.asarray(foto, dtype=np.float32) / 255
    a = analisar_escuro(px, caixa_logo)
    x0, y0, x1, y1 = caixa_logo
    fatia = (slice(y0 - 10, y1 + 10), slice(x0 - 10, x1 + 10))
    reg = px[fatia].copy()
    # a caixa inteira (só a parte que é produto) é refeita a partir do preto em volta
    corpo = a["corpo"][fatia] > 0.5
    caixa = np.zeros(corpo.shape, bool)
    caixa[10:-10, 10:-10] = True
    m = caixa & corpo
    peso = corpo.astype(np.float32)[..., None]     # o fundo azul não entra na média
    reg[m] = reg[corpo & ~m].mean(axis=0)
    for _ in range(800):
        soma = sum(np.roll(reg * peso, s, e) for s in (1, -1) for e in (0, 1))
        n = sum(np.roll(peso, s, e) for s in (1, -1) for e in (0, 1))
        media = soma / np.maximum(n, 1e-6)
        reg[m] = media[m]
    rng = np.random.default_rng(7)
    reg[m] += rng.normal(0, 0.008, reg[m].shape)
    px[y0 - 10:y1 + 10, x0 - 10:x1 + 10] = reg
    return Image.fromarray((np.clip(px, 0, 1) * 255).round().astype(np.uint8))


def recolorir_escuro(foto, hexcor, caixa_logo):
    """Pinta o corpo preto com a nova cor; o aço e o fundo ficam como estão.
    A logo prateada continua prateada em cores escuras e vira preta em cores claras."""
    px = np.asarray(foto, dtype=np.float32) / 255
    a = analisar_escuro(px, caixa_logo)
    lum, corpo = a["lum"], a["corpo"]
    med = np.median(lum[a["escuro"] > 0.9])
    cor = np.array([int(hexcor[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255
    # brilho relativo ao preto médio: realces clareiam, sombras escurecem
    luz = np.clip(1 + (lum - med) * 4.0, 0.45, 1.6)[..., None]
    tecido = np.clip(cor * luz, 0, 1)
    lg = a["logo"][..., None]
    lum_cor = 0.299 * cor[0] + 0.587 * cor[1] + 0.114 * cor[2]
    if lum_cor >= 0.45:
        # cor clara: bordado preto, mantendo o relevo da linha (os realces viram tons de preto)
        prata = np.clip((px - 0.05 * (1 - lg)) / np.maximum(lg, 0.08), 0, 1)
        logo_cor = 0.03 + prata * 0.17
    else:
        logo_cor = px          # cor escura: a logo prateada é mantida
    tecido = tecido * (1 - lg) + logo_cor * lg
    al = corpo[..., None]
    borda = (al > 0) & (al < 1)
    base = np.where(borda, a["fundo"], px)
    saida = base * (1 - al) + tecido * al
    return Image.fromarray((np.clip(saida, 0, 1) * 255).round().astype(np.uint8))


def salvar(img, nome):
    destino = PASTA / nome
    img.save(destino, quality=84, optimize=True, progressive=True)
    print(destino.name, destino.stat().st_size // 1024, "KB")


def main(so=None):
    """so: ids para gerar (ex.: ["moletom", "moletom-costas"]); vazio gera tudo."""
    quer = lambda id_: not so or id_ in so
    areas = {}
    for id_, cores in PRODUTOS.items():
        if not quer(id_):
            continue
        foto = Image.open(PASTA / f"{id_}.jpg").convert("RGB")
        liso, area = apagar_logo(foto)
        salvar(liso, f"{id_}-liso.jpg")
        w, h = foto.size
        x0, y0, x1, y1 = area
        areas[id_] = (round(x0 / w * 100, 1), round(y0 / h * 100, 1), round((x1 - x0) / w * 100, 1), round((y1 - y0) / h * 100, 1))
        for item in cores:
            nome, chave = item if isinstance(item, tuple) else (item, item)
            salvar(recolorir(foto, CORES[chave]), f"{id_}-{slug(nome)}.jpg")
            salvar(recolorir(liso, CORES[chave]), f"{id_}-liso-{slug(nome)}.jpg")
    for id_, cores in PRODUTOS_COM_LISO.items():
        if not quer(id_):
            continue
        foto = Image.open(PASTA / f"{id_}.jpg").convert("RGB")
        liso = Image.open(PASTA / f"{id_}-liso.jpg").convert("RGB")
        logo = logo_pela_diferenca(foto, liso)
        for item in cores:
            nome, chave = item if isinstance(item, tuple) else (item, item)
            salvar(recolorir(foto, CORES[chave], logo=logo), f"{id_}-{slug(nome)}.jpg")
            salvar(recolorir(liso, CORES[chave], sem_logo=True), f"{id_}-liso-{slug(nome)}.jpg")
    for id_, cores in PRODUTOS_SEM_LOGO.items():
        if not quer(id_):
            continue
        foto = Image.open(PASTA / f"{id_}.jpg").convert("RGB")
        for item in cores:
            nome, chave = item if isinstance(item, tuple) else (item, item)
            salvar(recolorir(foto, CORES[chave], sem_logo=True), f"{id_}-{slug(nome)}.jpg")
    for id_, cfg in PRODUTOS_ESCUROS.items():
        if not quer(id_):
            continue
        foto = Image.open(PASTA / f"{id_}.jpg").convert("RGB")
        caixa = cfg["logo"]
        liso = apagar_logo_escuro(foto, caixa)
        salvar(liso, f"{id_}-liso.jpg")
        w, h = foto.size
        x0, y0, x1, y1 = caixa
        areas[id_] = (round(x0 / w * 100, 1), round(y0 / h * 100, 1), round((x1 - x0) / w * 100, 1), round((y1 - y0) / h * 100, 1))
        for nome in cfg["cores"]:
            salvar(recolorir_escuro(foto, CORES[nome], caixa), f"{id_}-{slug(nome)}.jpg")
            salvar(recolorir_escuro(liso, CORES[nome], caixa), f"{id_}-liso-{slug(nome)}.jpg")
    print("\nLOGO_AREA (x, y, largura, altura em %):")
    for id_, (x, y, w, h) in areas.items():
        print(f'  {id_}: {{ x: {x}, y: {y}, w: {w}, h: {h} }},')


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
