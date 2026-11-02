// Leva quem abrir o endereço antigo (pontonobre.pages.dev) ou o www para o domínio principal,
// mantendo o caminho: links antigos de logo (/l/<id>) continuam funcionando.
// As prévias de deploy (<hash>.pontonobre.pages.dev) não são redirecionadas.

const DOMINIO = "pontonobrebordados.com.br";
const REDIRECIONAR = ["pontonobre.pages.dev", "www." + DOMINIO];

export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  if (REDIRECIONAR.includes(url.hostname)) {
    url.hostname = DOMINIO;
    url.protocol = "https:";
    url.port = "";
    return Response.redirect(url.toString(), 301);
  }
  return next();
}
