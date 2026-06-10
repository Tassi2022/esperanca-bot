import sys
import time
import logging
import schedule
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    PIZZARIA_NOME, PIZZARIA_HISTORIA, PIZZARIA_IFOOD, PIZZARIA_BAIRRO,
    HASHTAGS, PALAVRAS_CHAVE, PALAVRAS_URGENTES,
    HORARIO_RELATORIO, INTERVALO_VARREDURA_MINUTOS, GEMINI_API_KEY,
)
from src.monitor_instagram import coletar_todas_hashtags
from src.gerador_resposta import gerar_resposta
from database import salvar_oportunidade, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

posts_enviados = set()
init_db()

def varredura():
    global posts_enviados
    logger.info("Iniciando varredura...")
    posts = coletar_todas_hashtags(HASHTAGS, PALAVRAS_CHAVE, PALAVRAS_URGENTES)
    novos = [p for p in posts if p["id"] not in posts_enviados]
    logger.info(f"{len(novos)} posts novos encontrados")
    for post in novos:
        posts_enviados.add(post["id"])
        resposta = gerar_resposta(
            post=post,
            pizzaria_nome=PIZZARIA_NOME,
            pizzaria_historia=PIZZARIA_HISTORIA,
            pizzaria_ifood=PIZZARIA_IFOOD,
            pizzaria_bairro=PIZZARIA_BAIRRO,
            gemini_api_key=GEMINI_API_KEY,
        )
        salvar_oportunidade(post, resposta)
        logger.info(f"Salvo no dashboard: {post['link']}")
        time.sleep(1)
    return novos

def main_loop():
    logger.info(f"Bot A EsperancA iniciado -- {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    schedule.every(INTERVALO_VARREDURA_MINUTOS).minutes.do(varredura)
    varredura()
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--agora" in args:
        varredura()
    else:
        main_loop()