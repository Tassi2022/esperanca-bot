import requests
import logging
logger = logging.getLogger(__name__)

ZAPI_SECURITY_TOKEN = "F1731976815fe404fabcc7c279b4b3413S"

def enviar_mensagem(texto, destino, zapi_instance_id, zapi_token, **kwargs):
    url = f"https://api.z-api.io/instances/{zapi_instance_id}/token/{zapi_token}/send-text"
    headers = {
        "Content-Type": "application/json",
        "client-token": ZAPI_SECURITY_TOKEN
    }
    try:
        resp = requests.post(url, json={"phone": destino, "message": texto}, headers=headers, timeout=15)
        if resp.status_code in (200, 201):
            logger.info(f"Mensagem enviada para {destino}")
            return True
        logger.error(f"Erro: {resp.status_code} - {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Falha Z-API: {e}")
        return False

def formatar_alerta_urgente(post, resposta):
    return (
        f"URGENTE -- A EsperancA\n\n"
        f"Hashtag: #{post['hashtag_origem']}\n"
        f"Postado: {post['timestamp_fmt']}\n\n"
        f"Post:\n{post['texto'][:200]}\n\n"
        f"Resposta sugerida:\n{resposta}\n\n"
        f"Abrir post: {post['link']}"
    )

def formatar_relatorio_diario(oportunidades):
    if not oportunidades:
        return "Relatorio diario -- A EsperancA\n\nNenhuma oportunidade hoje. Monitoramento ativo!"
    urgentes = [o for o in oportunidades if o.get("urgente")]
    normais = [o for o in oportunidades if not o.get("urgente")]
    linhas = [
        f"Relatorio diario -- A EsperancA",
        f"{len(oportunidades)} oportunidades encontradas",
        f"Urgentes: {len(urgentes)} | Normais: {len(normais)}\n",
    ]
    if urgentes:
        linhas.append("URGENTES:")
        for i, op in enumerate(urgentes[:5], 1):
            linhas.append(f"{i}. {op['texto'][:80]}...\n   {op['link']}\n   {op.get('resposta_sugerida','')[:100]}...\n")
    if normais:
        linhas.append("OUTRAS:")
        for i, op in enumerate(normais[:5], 1):
            linhas.append(f"{i}. {op['texto'][:80]}...\n   {op['link']}\n")
    linhas.append("\niFood: https://ifoodbr.onelink.me/F4X4/AEsperancaPizzaria")
    return "\n".join(linhas)
