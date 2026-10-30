// Recebe a logo (PNG já sem fundo) que o cliente enviou no site e devolve o link dela.
// O link vai na mensagem do orçamento no WhatsApp e aparece como cartão com a logo.
// Depois, o site manda a capa da prévia (JPEG) com o cabeçalho x-capa-de: <id>.

const TAMANHO_MAX = 3 * 1024 * 1024;        // 3 MB
const VALIDADE = 60 * 60 * 24 * 180;        // a logo fica guardada por 180 dias
const PNG = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
const JPEG = [0xff, 0xd8, 0xff];

const resposta = (dados, status = 200) =>
  new Response(JSON.stringify(dados), { status, headers: { "content-type": "application/json; charset=utf-8" } });

const comeca = (buf, assinatura) => {
  const b = new Uint8Array(buf, 0, Math.min(assinatura.length, buf.byteLength));
  return assinatura.every((v, i) => b[i] === v);
};

export async function onRequestPost({ request, env }) {
  const tipo = request.headers.get("content-type") || "";
  const dados = await request.arrayBuffer();
  if (dados.byteLength === 0 || dados.byteLength > TAMANHO_MAX) {
    return resposta({ erro: "A imagem precisa ter até 3 MB." }, 413);
  }

  // capa da prévia de uma logo já guardada (só uma vez por logo)
  const capaDe = request.headers.get("x-capa-de");
  if (capaDe) {
    if (!/^[a-f0-9]{16}$/.test(capaDe) || !tipo.startsWith("image/jpeg") || !comeca(dados, JPEG)) {
      return resposta({ erro: "Capa inválida." }, 415);
    }
    const { value: logo, metadata } = await env.LOGOS.getWithMetadata(capaDe, "arrayBuffer");
    if (!logo) return resposta({ erro: "Logo não encontrada." }, 404);
    if (metadata && metadata.capa) return resposta({ erro: "Capa já enviada." }, 409);
    await env.LOGOS.put(`${capaDe}-capa`, dados, { expirationTtl: VALIDADE });
    // marca na logo que ela tem capa
    await env.LOGOS.put(capaDe, logo, { expirationTtl: VALIDADE, metadata: { ...(metadata || {}), capa: true } });
    return resposta({ ok: true });
  }

  if (!tipo.startsWith("image/png") || !comeca(dados, PNG)) {
    return resposta({ erro: "Envie a logo em PNG." }, 415);
  }
  const id = crypto.randomUUID().replace(/-/g, "").slice(0, 16);
  const nome = decodeURIComponent(request.headers.get("x-nome") || "logo.png").slice(0, 120);
  await env.LOGOS.put(id, dados, { expirationTtl: VALIDADE, metadata: { nome } });

  return resposta({ id, url: new URL(`/l/${id}`, request.url).href });
}
