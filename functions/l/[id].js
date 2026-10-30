// Página da logo enviada no orçamento: https://pontonobre.pages.dev/l/<id>
// No WhatsApp, o link vira um cartão com a capa; ao abrir, mostra a logo grande com botão de baixar.

const esc = t => String(t).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export async function onRequestGet({ params, env, request }) {
  const id = String(params.id || "");
  if (!/^[a-f0-9]{16}$/.test(id)) return new Response("Logo não encontrada.", { status: 404 });
  const { value, metadata } = await env.LOGOS.getWithMetadata(id, "arrayBuffer");
  if (!value) {
    return new Response("Esta logo não está mais disponível (os arquivos ficam guardados por 180 dias).",
      { status: 404, headers: { "content-type": "text/plain; charset=utf-8" } });
  }
  const origem = new URL(request.url).origin;
  const nome = esc(metadata && metadata.nome ? metadata.nome : "logo.png");
  const png = `${origem}/logo/${id}.png`;
  const capa = metadata && metadata.capa ? `${origem}/logo/${id}-capa.jpg` : png;

  const html = `<!doctype html>
<html lang="pt-BR">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Logo para orçamento · Ponto Nobre</title>
<meta property="og:type" content="website">
<meta property="og:site_name" content="Ponto Nobre">
<meta property="og:title" content="Logo para orçamento">
<meta property="og:description" content="${nome} · enviada pelo site da Ponto Nobre">
<meta property="og:image" content="${capa}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/icone-32.png">
<style>
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #04060c; color: #eef2fb;
         font: 16px/1.5 "Segoe UI", system-ui, sans-serif; padding: 24px; box-sizing: border-box; }
  main { width: min(640px, 100%); display: grid; gap: 18px; text-align: center; }
  .quadro { border-radius: 16px; border: 1px solid #1b2744; padding: 28px;
            background: repeating-conic-gradient(#e9ecf1 0 25%, #ffffff 0 50%) 0 0 / 22px 22px; }
  .quadro img { max-width: 100%; max-height: 60vh; display: block; margin: 0 auto; }
  h1 { margin: 0; font-size: 20px; }
  p { margin: 0; color: #8f9bb8; font-size: 14px; overflow-wrap: anywhere; }
  .acoes { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
  a { display: inline-block; padding: 12px 18px; border-radius: 10px; font-weight: 700; text-decoration: none; }
  .baixar { background: #1f6bff; color: #fff; }
  .site { border: 1px solid #1b2744; color: #eef2fb; }
</style>
<main>
  <h1>Logo enviada para orçamento</h1>
  <p>${nome}</p>
  <div class="quadro"><img src="${png}" alt="Logo enviada pelo cliente"></div>
  <div class="acoes">
    <a class="baixar" href="${png}" download="${nome}">Baixar PNG</a>
    <a class="site" href="${origem}/">Ir para o site</a>
  </div>
  <p>PNG sem fundo · disponível por 180 dias a partir do envio.</p>
</main>
</html>`;
  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=300" } });
}
