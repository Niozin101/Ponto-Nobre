# Ponto Nobre — uniformes e brindes personalizados

Site de catálogo e orçamento da **Ponto Nobre**, que faz camisas, polos, suéteres, moletons, baby looks, mochilas, copos Stanley e chaveiros com a logo de empresas. O cliente envia a logo, vê na hora como ela fica em cada peça, monta o pedido e recebe o orçamento pelo WhatsApp.

**No ar:** https://pontonobrebordados.com.br

## O que o site faz

- **Prévia com a logo do cliente.** Qualquer imagem serve: o fundo é removido no próprio navegador e a logo aparece em todas as peças, nas cores escolhidas.
- **Cara de bordado.** Um filtro SVG dá textura de linha, relevo e sombra no tecido à logo enviada. No copo, a logo sai prateada como gravação a laser.
- **Até 10 logos por peça**, cada uma num lugar (peito, centro, mangas, costas). A partir da 7ª, as logos extras entram embaixo das que já estão no lugar.
- **Editor "Ajustar na peça".** Arrastar para mover, puxar o canto para o tamanho, girar e pinça com dois dedos no celular. O ajuste é por peça, e "Usar em todas" copia para as outras.
- **Chaveiro em 3D de verdade** (three.js). O contorno da logo vira uma peça impressa em 3D, com linhas de camada, logo em relevo, argola de metal passando pelo furo e escolha da cor da logo, inclusive dourado e prata. Dá para girar 360° arrastando.
- **Orçamento pelo WhatsApp.** A mensagem sai pronta, com peças, tamanhos, cores, lugar e ajustes de cada logo. A logo vai como link (guardada no Cloudflare KV), com prévia no WhatsApp.
- **Kits prontos** (boas-vindas, evento…) e carrinho que fica salvo no navegador.

## Como é feito

- **Um único `index.html`**, com HTML, CSS e JavaScript puros, sem framework nem etapa de build. O three.js só é baixado quando o chaveiro aparece.
- **Cloudflare Pages** para hospedar e **Pages Functions** (`functions/`) para guardar a logo enviada e gerar o link com prévia.
- **Ferramentas em Python** (`ferramentas/`, com Pillow e NumPy) para preparar as fotos dos produtos:
  - `preparar_fotos.py` — enquadra a peça no padrão do site (1200×900, fundo azul, sombra);
  - `tirar_logo.py` — apaga a logo de uma foto, preenchendo com o tecido em volta;
  - `gerar_cores.py` — gera cada cor do catálogo a partir da foto branca, mantendo dobras e sombras, com e sem logo;
  - `gerar_compartilhamento.py` — imagem de prévia para redes sociais.

## Estrutura

```
index.html          o site inteiro
assets/             logo, ícones e fotos dos produtos (os arquivos com "_" são as fotos originais)
functions/          Cloudflare Pages Functions (envio da logo e link de prévia)
ferramentas/        scripts Python para preparar as fotos
wrangler.toml       configuração do Cloudflare Pages
```

## Rodar e publicar

```bash
# ver o site no computador
python -m http.server 8123

# publicar: a pasta "publicar" recebe o index.html e os assets, e o wrangler envia
mkdir -p publicar && cp -r index.html assets publicar/
npx wrangler pages deploy --branch main
```

O envio da logo para o WhatsApp precisa das Functions e do KV do Cloudflare. No servidor local, a prévia funciona, mas a mensagem pede o arquivo na conversa.
