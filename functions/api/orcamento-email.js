// Quando o cliente toca em "Enviar pelo WhatsApp", o site também manda o pedido para cá,
// e a loja recebe um e-mail com o texto do orçamento e as logos anexadas (pegas do KV).
// Segredos no Cloudflare (Settings → Variables and Secrets): RESEND_API_KEY e EMAIL_ORCAMENTO.
// Sem eles, a função não faz nada e o WhatsApp segue normal.

const MAX_TEXTO = 6000;
const MAX_LOGOS = 10;
const MAX_ANEXOS = 20 * 1024 * 1024;   // soma das logos anexadas
const POR_IP_HORA = 5;                 // e-mails por pessoa a cada hora
const POR_DIA = 90;                    // o plano grátis do Resend manda até 100 por dia

const resposta = (dados, status = 200) =>
  new Response(JSON.stringify(dados), { status, headers: { "content-type": "application/json; charset=utf-8" } });

const esc = t => String(t).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const base64 = buf => {
  const b = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(s);
};

async function resumo(texto) {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return [...new Uint8Array(h)].slice(0, 12).map(x => x.toString(16).padStart(2, "0")).join("");
}

// Conta um envio na chave; devolve false se passou do limite
async function dentroDoLimite(kv, chave, max, ttl) {
  const n = Number(await kv.get(chave)) || 0;
  if (n >= max) return false;
  await kv.put(chave, String(n + 1), { expirationTtl: ttl });
  return true;
}

export async function onRequestPost({ request, env }) {
  if (!env.RESEND_API_KEY || !env.EMAIL_ORCAMENTO) return resposta({ ok: false, motivo: "desligado" });

  // só aceita pedidos vindos do próprio site
  const origem = request.headers.get("origin");
  if (origem && origem !== new URL(request.url).origin) return resposta({ erro: "Origem não permitida." }, 403);

  let dados;
  try { dados = JSON.parse(await request.text()); } catch (e) { return resposta({ erro: "Pedido inválido." }, 400); }
  const texto = String(dados.mensagem || "").trim();
  if (!texto || texto.length > MAX_TEXTO) return resposta({ erro: "Mensagem inválida." }, 400);
  const pedidas = (Array.isArray(dados.logos) ? dados.logos : []).slice(0, MAX_LOGOS)
    .filter(l => l && /^[a-f0-9]{16}$/.test(l.id));

  // o mesmo pedido tocado duas vezes seguidas vai uma vez só
  const marca = `email:${await resumo(texto + pedidas.map(l => l.id).join())}`;
  if (await env.LOGOS.get(marca)) return resposta({ ok: true, repetido: true });

  const ip = request.headers.get("cf-connecting-ip") || "sem-ip";
  const hora = new Date().toISOString().slice(0, 13), dia = hora.slice(0, 10);
  if (!await dentroDoLimite(env.LOGOS, `limite:${ip}:${hora}`, POR_IP_HORA, 60 * 60 * 2)) return resposta({ erro: "Muitos envios. Tente mais tarde." }, 429);
  if (!await dentroDoLimite(env.LOGOS, `limite:dia:${dia}`, POR_DIA, 60 * 60 * 48)) return resposta({ erro: "Limite do dia atingido." }, 429);

  const anexos = [];
  let total = 0;
  for (const [i, l] of pedidas.entries()) {
    const { value, metadata } = await env.LOGOS.getWithMetadata(l.id, "arrayBuffer");
    if (!value || total + value.byteLength > MAX_ANEXOS) continue;
    total += value.byteLength;
    const nome = String((metadata && metadata.nome) || "logo.png").replace(/[^\w.\- ]/g, "_").slice(0, 80);
    anexos.push({ filename: `${i + 1}-${nome}`, content: base64(value) });
  }

  const nomeCliente = (texto.match(/^Nome: (.+)$/m) || [])[1];
  const totalPecas = (texto.match(/^Total: (.+)$/m) || [])[1];
  const assunto = `Novo orçamento${totalPecas ? `: ${totalPecas}` : ""}${nomeCliente ? ` (${nomeCliente})` : ""}`.slice(0, 150);
  const html = `<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.5;color:#1d2433">
<p style="margin:0 0 12px"><b>Um cliente acabou de tocar em "Enviar pelo WhatsApp" no site.</b><br>
Se a mensagem não chegar no WhatsApp, o pedido está todo aqui.</p>
<pre style="white-space:pre-wrap;font-family:inherit;background:#f3f5f9;padding:14px;border-radius:8px;margin:0">${esc(texto)}</pre>
<p style="margin:12px 0 0;color:#5a6478">${anexos.length ? `${anexos.length === 1 ? "A logo do cliente está anexada" : `As ${anexos.length} logos do cliente estão anexadas`} (PNG sem fundo).` : "O cliente não enviou logo pelo site."}</p>
</div>`;

  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: env.EMAIL_REMETENTE || "Ponto Nobre <onboarding@resend.dev>",
      to: [env.EMAIL_ORCAMENTO],
      subject: assunto,
      html,
      text: texto,
      attachments: anexos
    })
  });
  if (!r.ok) {
    console.error("Resend recusou o e-mail:", r.status, await r.text());
    return resposta({ erro: "Não foi possível enviar o e-mail." }, 502);
  }
  await env.LOGOS.put(marca, "1", { expirationTtl: 600 });
  return resposta({ ok: true, anexos: anexos.length });
}
