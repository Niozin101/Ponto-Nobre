// Arquivos guardados das logos:
//   /logo/<id>.png        a logo (PNG sem fundo), para ver e baixar
//   /logo/<id>-capa.jpg   a capa que aparece na prévia do link no WhatsApp

export async function onRequestGet({ params, env }) {
  const nomeArq = String(params.id || "");
  const capa = nomeArq.match(/^([a-f0-9]{16})-capa\.jpg$/);
  const logo = nomeArq.match(/^([a-f0-9]{16})\.png$/);
  if (!capa && !logo) return new Response("Logo não encontrada.", { status: 404 });

  if (capa) {
    const value = await env.LOGOS.get(`${capa[1]}-capa`, "arrayBuffer");
    if (!value) return new Response("Capa não encontrada.", { status: 404 });
    return new Response(value, { headers: { "content-type": "image/jpeg", "cache-control": "public, max-age=86400" } });
  }

  const { value, metadata } = await env.LOGOS.getWithMetadata(logo[1], "arrayBuffer");
  if (!value) return new Response("Logo não encontrada ou expirada.", { status: 404 });
  const nome = (metadata && metadata.nome ? metadata.nome : `logo-${logo[1]}.png`).replace(/[^\w.\- ]/g, "_");
  return new Response(value, {
    headers: {
      "content-type": "image/png",
      "cache-control": "public, max-age=86400",
      "content-disposition": `inline; filename="${nome}"`
    }
  });
}
